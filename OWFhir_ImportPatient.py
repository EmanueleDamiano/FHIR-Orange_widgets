import tkinter as tk
from Orange.data import Domain, StringVariable, DiscreteVariable, ContinuousVariable, Table
from Orange.widgets import widget, gui
from tkinter import filedialog
import json
from Orange.widgets.utils import widgetpreview
import re 
import requests
import pandas as pd 

class OWFhirAnalyziePatient(widget.OWWidget):
    name = "import fhir patient resource"
    description = "returns processed orange table for patient FHIR resource"
    category = "FHIR Widgets"
    want_main_area=True
    icon = "icons/patient_icon.PNG"

    class Inputs:
        list_of_paths = widget.Input("Bundle Resource Paths", list)

    class Outputs:
        processed_table = widget.Output("Processed Patient Table", Table)


    def __init__(self):
        super().__init__()
        self.all_res = [] 
        self.all_keys = [] 
        self.addPrefix = False 
        
        box = gui.widgetBox(self.mainArea,"")
        box.setFixedHeight(100)
        
        ## input field for string of the endpoint of the server
        self.test_input = "" ## inital default value for input
        self.local_resource_path = ""
        self.input_line = gui.lineEdit(widget=box, master=self,value="test_input", label="Input a fhir server endpoit to retrieve data for a patient ",validator=None)
        gui.button(box, master = self, label = "send", callback=self.validate_api)

        gui.separator(self)
        box2  = gui.widgetBox(self.mainArea,"")
        box2.setFixedHeight(50)
        self.display_message = gui.widgetLabel(box2," ")        
        self.upload_button = gui.button(box2, self, label="Import one or more PATIENT resource", callback=self.selectMedicationRequests)
        gui.separator(self)
    
    def selectMedicationRequests(self):
        self.local_resource_path = filedialog.askopenfilenames(title="Select JSON file(s)", filetypes=(("JSON files", "*.json"),))
        if self.local_resource_path:
            self.set_input(self.local_resource_path)
    
    def validate_api(self):
        ## check if the input string is a in the format for making an API request
        api_pattern = r'^https?://(?:\w+\.)?\w+\.\w+(?:/\S*)?$'
        if re.match(api_pattern, self.test_input):
            self.make_request()
        else:
            print("input a valid fhir api")
            self.display_message.setText("ERROR: Input a valid FHIR API")


    def make_request(self):
        try:
            response = requests.get(self.test_input)
        except:
            print("error while making request")
            self.display_message.setText("error while making request")
            return
        json_results = response.json()
        
        medication_requests = self.extract_MedicationRequest(res_from_request=json_results)
        processed_resources = list(map(self.flatten_dict, medication_requests))
        [self.all_res.append(resource) for resource in processed_resources]
        self.create_table()
        
    def flatten_dict(self,d, key ='', sep='_'):
        
        items = []
        for k, v in d.items():
            new_key = key + sep + k if key else k
            if new_key not in self.all_keys:
                self.all_keys.append(new_key)
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                for i, val in enumerate(v):
                    if isinstance(val, dict):
                        items.extend(self.flatten_dict(val, f"{new_key}_{i}", sep=sep).items())
                    else:
                        items.append((f"{new_key}_{i}", val))
                
            else:
                items.append((new_key, v))
        
        return dict(items)
            


    def make_domain(self):
        self.df = pd.DataFrame(self.all_res)
        if self.addPrefix:
            self.df = self.df.add_prefix("resource_")
        self.df.columns = self.df.columns.str.replace(r'^resource_', 'Patient_', regex=True)

        ## making the resource more readable 
        self.df = self.df.rename(columns={
            "Patient_extension_3_valueCode"             :"Patient_gender_code",
            "Patient_extension_3_valueString"           :"Patient_full_display_name",
            "Patient_extension_4_valueAddress_country"  :"Patient_address_country",

        })


        self.df = self.df.fillna("nan")
        numeric_columns = self.df.select_dtypes(include=["int", "float"])
        metas_columns   = set(self.df.columns) - set(numeric_columns)
        numeric_variables = []
        metas_variables = []
        list(map(lambda x : metas_variables.append(StringVariable(name=x)),metas_columns))
        list(map(lambda x : numeric_variables.append(ContinuousVariable(name=x)),numeric_columns))
        domain = Domain(numeric_variables , metas = metas_variables)
        return domain


    def extract_PatientResource(self, path=None,res_from_request=None):
        if path is not None:
            with open(path,"r") as f:
                bundle_data = json.load(f)
                f.close()   
        else:
            bundle_data = res_from_request
        try:
            patient_resources  = bundle_data["entry"]
            idx_patient_res = map(lambda resource: resource["resource"]["resourceType"] == "Patient", patient_resources) 
            list_patients = [element for element, _ispatient in zip(patient_resources, idx_patient_res) if _ispatient]
            # print(f"processing a total of {len(list_med_request)} medication requests found in the file")
        except KeyError:
            self.addPrefix = True
            list_patients = [element for element in [bundle_data]]
        
        return list_patients
    
    
        
    def create_table(self):
        domain = self.make_domain()
        ordered_domain = []
        for i in range(len(domain.attributes)):
            ordered_domain.append(domain.attributes[i].name)
        for i in range(len(domain.metas)):
            ordered_domain.append(domain.metas[i].name)
        data_list = [list(map(str,row)) for row in self.df[ordered_domain].to_numpy()]
        self.Outputs.processed_table.send(Table(domain, data_list))

    @Inputs.list_of_paths
    def set_input(self, value): 
        
        self.input_value = value
        if self.input_value is not None :
        
            for path in self.input_value:
                
                patients = self.extract_PatientResource(path)
                processed_resources = list(map(self.flatten_dict, patients))
                [self.all_res.append(resource) for resource in processed_resources]
            self.create_table()

        
## for testing the widget without having to run Orange. 
if __name__ == "__main__":
    widgetpreview.WidgetPreview(OWFhirAnalyziePatient).run()
        

