from Orange.data import Domain, StringVariable, DiscreteVariable, ContinuousVariable, Table
from Orange.widgets import widget, gui
from Orange.widgets.utils.signals import Input, Output
from tkinter import filedialog
from Orange.widgets.utils import widgetpreview
import pandas as pd 
from openai import OpenAI, BadRequestError
from Orange.widgets.utils import widgetpreview
import numpy as np 
from Orange.widgets.settings import Setting
from AnyQt.QtWidgets import QTextEdit, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt
import re
import sys
from io import StringIO   

class OWAIWidget_Full(widget.OWWidget):
    name = "FHIR LLAMA"
    description = "analyze FHIR resources using LLM"
    category = "FHIR Widgets"
    want_main_area = True
    icon = "icons/FHIR_Llama_icon.svg"

    api_token   = Setting("")
    user_prompt = Setting("")

    class Inputs:
        fhir_resources = widget.Input("Orange table for applying", Table)

    class Outputs:
        output_table = widget.Output("Orange table after execution", Table)


    def __init__(self):
        super().__init__()

        container_widget = QWidget(self.controlArea)
        container_layout = QVBoxLayout(self.controlArea)
        container_layout.setAlignment(Qt.AlignCenter) 


        ## api token input area (controlarea)
        self.user_api_token = gui.lineEdit(widget=self.controlArea, master=self, 
             value="api_token", label="API TOKEN for using LLM")
        
        self.connect_button = gui.button(widget=self.controlArea, master=self, 
                label="connect", callback=self.initialize_client)
        self.connected_string = gui.widgetLabel(self.controlArea, "NOT CONNECTED TO LLM")
        container_layout.layout().addWidget(container_widget)
        ## main area:
        self.input_prompt_box = gui.widgetBox(self.mainArea,"")
        self.input_prompt = gui.lineEdit(widget=self.input_prompt_box, master=self, 
             value="user_prompt", label="insert your question here"
             ) 
        self.generate_code_button = gui.button(self.input_prompt_box, master = self, label = "send query", callback=self.generate_code)
        self.generated_code_area = QTextEdit(self.mainArea)
        self.generated_code_area.setReadOnly(False)  
        self.generated_code_area.setMinimumHeight(100)
        self.generated_code_area.setMinimumWidth(300)
        
        self.mainArea.layout().addWidget(self.generated_code_area)
        self.execute_button = gui.button(widget=self.mainArea, master=self, 
                                         label = "EXECUTE CODE", callback=self.execute_code)
        
        self.display_box = gui.widgetBox(self.mainArea,"")
        self.display_response =  gui.widgetLabel(self.display_box, "")
        self.display_box.setFixedHeight(100)
        self.mainArea.layout().addWidget(self.display_box)


    @Inputs.fhir_resources
    def orange_table_to_pandas(self,orange_table):
        ## attributes in the orage table domain : 
        ## metas => string variables
        ## X => discrete, continuous variables


        _metas_columns  = [var.name for var in orange_table.domain.metas]
        ## getting discrete attributes to decode 
        discr_attributes_idx = []
        discr_attributes     = []
        for idx,var in enumerate(orange_table.domain.attributes):
            if var.is_discrete:
                discr_attributes.append(var)
                discr_attributes_idx.append(idx)
        
        ## getting pandas df from metas attributes
        metas_obj = {}
        metas_data = orange_table.metas.reshape(len(orange_table),-1)
        for idx, meta_attr in enumerate(_metas_columns):
            metas_obj[meta_attr] = metas_data[:,idx]
        metas_df = pd.DataFrame(metas_obj)

        ## getting decoded data from discrete attributes 
        categorical_columnns = np.array(orange_table.domain)[discr_attributes_idx]
        decoded_values = {}
        for attr,idx in zip(categorical_columnns,discr_attributes_idx):
            decoded_column = []
            for val in orange_table.X[:,idx]:
                if np.isnan(val):
                    decoded_column.append("nan")
                else:
                    decoded_column.append(attr.values[int(val)])
            decoded_values[attr.name] = decoded_column
        categorical_df = pd.DataFrame(decoded_values)
        X = pd.concat([metas_df, categorical_df],axis=1)

        ## attaching numerical data 
        num_attributes_idx = [i for i in range(orange_table.X.shape[1]) if i not in discr_attributes_idx ]
        num_columns = np.array(orange_table.domain.attributes)[num_attributes_idx]
        numerical_df = pd.DataFrame(data=orange_table.X[:,num_attributes_idx], columns=[var.name for var in num_columns])
        self.table = pd.concat([X,numerical_df], axis=1)


    def initialize_client(self):
        
        client = OpenAI(
            api_key = self.user_api_token.text(),
            base_url = "https://api.llama-api.com"
        )
        self.connected_string.setText("CONNECTED TO LLM")
        return client



    def create_output_table(self):
        ## create table domain of the output Orange table 
        ## all the variables are formatted as meta for a faster processing
        ## important to invoke this function after execute_code() 
        domain = list(self.table.columns)
        domain_variables = []
        list(map(lambda x : domain_variables.append(StringVariable(name=x)),domain))
        domain_for_table = Domain(attributes=[],metas = domain_variables)
        data_list = [list(map(str,row)) for row in self.table[domain].to_numpy()]
        orange_out_table = Table.from_list(domain_for_table, data_list)
        self.Outputs.output_table.send(orange_out_table)

    def apply_code(self):
        ## store self.table in global scope for avoiding function callig issues
        globals()["temp_table"] = self.table
        exec(self.final_code,globals())
        ## removing table from globals after code execution
        self.table = globals().pop('temp_table')

    def execute_code(self):

        self.final_code = self.generated_code_area.toPlainText()
        print("response for this prompt: ", self.user_prompt)
        print("final code = ", self.final_code)
        
        old_stdout = sys.stdout
        redirected_output = StringIO()
        sys.stdout = redirected_output
        table = self.table
        try:
            # Execute the code with exec
            self.apply_code()
            
        except Exception as e:
            print(f"Error occurred: {e}")
            ## self.check_dependencies()
        except ModuleNotFoundError as e:
            print("trying to install python packages... \n",e )

        finally:
            # Reset stdout
            sys.stdout = old_stdout

        # Get the captured output
        output = redirected_output.getvalue()

        # Display the output in the QTextEdit area
        self.display_response.setText(f"{self.user_prompt} \n {output}")
        ## clear editable area 
        self.generated_code_area.clear()
        self.create_output_table()

    def code_refine(self,client,code_to_check,analysis_prompt_template="solve errors I could get applying this code {gen_code} to this table {data_table}"):
        system_prompt_template = """
            You are a skilled assistant in debugging python code. Return only python code, no english sentences, if the code is fine return it again.   
        """
        final_prompt = analysis_prompt_template.format(gen_code = code_to_check, data_table = self.table)

        # print("REFINEMENT USER PROMPT  : ", final_prompt)
        response = client.chat.completions.create(
            model="llama3.1-70b", 
            messages=[
                {"role": "system", "content": system_prompt_template},
                {"role": "user", "content": final_prompt}
            ],
        )
        response = response.choices[0].message.content
        return response


    def generate_code(self):
        pre_prompt = """
                    You are a specialized FHIR data processing assistant. Your task is to generate Python code for legitimate data operations.
                    The user will pass you a pandas dataframe containing the set of FHIR resources and its request. 
                    Carefully evaluate the input request following this steps:

                    1- Ensure the request is for a legitimate helthcare data analysis.
                    2- Determine if it involves operations on any FHIR resources for information extraction or visualization. 
                    3. Ensure the request does not involve system access, file operations outside FHIR data, or security exploitation

                    If you consider the request as legit reply by only providing the python code for solving the request, without any english sentence.
                    If the request is NOT about FHIR data operations: Return exactly "NOT ALLOWED".
                    If the request involves file system access, credential extraction, or system manipulation: Return exactly "NOT ALLOWED"
                    """
        prompt_template = """
            this is the 'temp_table' dataframe: {sub_table}. {prompt}
        """
        prompt = self.input_prompt.text()

        client = self.initialize_client()
        final_prompt = prompt_template.format(sub_table = self.table.iloc[:1,:], prompt = prompt)
        print("USER PROMPT IN THE FIRST CALL: ", final_prompt)
        response = client.chat.completions.create(
            model= "llama3.1-70b",
            messages=[
                {"role": "system", "content": f"{pre_prompt}"}, ## 
                {"role": "user", "content": f"{final_prompt}"},
                ])
        
        generated_code = response.choices[0].message.content
        generated_code = re.sub("```", "", generated_code)
        generated_code = re.sub("python", '', generated_code, flags=re.IGNORECASE)
        print("first call generated code after cleaning: ", generated_code)
        try:
            generated_code = self.code_refine(client,generated_code)
        except BadRequestError:
            print("code not refined due to bad request error")
        except Exception as e:
            print(f"code not refined: {e}")
        generated_code = re.sub("```", "", generated_code)
        generated_code = re.sub("python", '', generated_code, flags=re.IGNORECASE)
        print("CODE AFTER SELF and cleaning: \n", generated_code)
        ## display generated code in the editable area
        self.generated_code_area.append(f"{generated_code}")

        
## for testing the widget without having to run Orange. 
if __name__ == "__main__":
    widgetpreview.WidgetPreview(OWAIWidget_Full).run()