from Orange.data import Domain, StringVariable, DiscreteVariable, ContinuousVariable, Table
from Orange.widgets import widget, gui
from Orange.widgets.utils.signals import Input, Output
from tkinter import filedialog
import json
from Orange.widgets.utils import widgetpreview
import re 
import requests
import pandas as pd 

class OWFhirImportObservation(widget.OWWidget):
    name = "Import Observation FHIR Resources"
    description = "returns processed orange table for Observation FHIR resource"
    category = "FHIR Widgets"
    icon = "icons/observation_icon_no_bg.png"

    class Inputs:
        list_of_paths = widget.Input("Bundle Resource Paths", list)

    class Outputs:
        processed_table = widget.Output("Processed Observations Table", Table)


    def __init__(self):
        super().__init__()
        
        self.string_variables = ["observation_full_id", "observation_id","observation_subject_reference","observation_encounter_reference",
                                  "resource_effectiveDateTime", "resource_issued", "resource_valueQuantity_unit"]
        self.numeric_variables = ["resource_valueQuantity_value"]
        self.cat_variables = ["resource_status", "resource_category_0_coding_0_code","resource_category_0_coding_0_display",
                              "resource_code_coding_0_code","resource_code_coding_0_display"]
        self.all_res = [] 
        self.all_keys = [] 
        self.addPrefix = False 

        ##  GUI

        box = gui.widgetBox(self.controlArea,"")
        box.setFixedHeight(100)
        self.test_input = "" ## inital default value for input
        self.local_resource_path = ""
        self.input_line = gui.lineEdit(widget=box, master=self,value="test_input", label="Input a fhir server endpoit to retrieve data ",validator=None)
        gui.button(box, master = self, label = "send", callback=self.validate_api)

        gui.separator(self)
        box2  = gui.widgetBox(self.controlArea,"")
        box2.setFixedHeight(50)
        self.display_message = gui.widgetLabel(box2," ")        
        self.upload_button = gui.button(box2, self, label="Import one or more observation resources", callback=self.selectObservations)
        
        gui.separator(self)
        


    def selectObservations(self):
        self.local_resource_path = filedialog.askopenfilenames(title="Select JSON file(s)", filetypes=(("JSON files", "*.json"),))
        if self.local_resource_path:
            self.set_input(self.local_resource_path)



    def validate_api(self):
        api_pattern = r'^https?://(?:\w+\.)?\w+\.\w+(?:/\S*)?$'
        if re.match(api_pattern, self.test_input):
            self.make_request()
        else:
            self.display_message.setText("ERROR: Input a valid FHIR API")


    def make_request(self):
        try:
            response = requests.get(self.test_input)
        except:
            self.display_message.setText("error while making request")
            return
        json_results = response.json()
        medication_requests = self.extract_Observations(res_from_request=json_results)
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
            


    def make_cat_variables(self):
        processed_cat_variables = []
        
        valid_columns = [col for col in self.cat_variables if col in self.df.columns]

        cat_x = self.df[valid_columns]
        for column in cat_x:
            cat_x.loc[:,column] = list(map(str,cat_x[column]))
            processed_cat_variables.append(DiscreteVariable(name = str(column), values = list(pd.unique(cat_x[column]))))
        return processed_cat_variables

    def make_domain(self):
        self.df = pd.DataFrame(self.all_res)
        
        ## rename the id column for not causing misunderstanding in the merge operation
        self.df = self.df.rename(columns={"resource_id" : "observation_id",
                                          "resource_subject_reference":"observation_subject_reference",
                                          "resource_encounter_reference":"observation_encounter_reference"})
        
        ## add column for matching the format of reference field iin other resources
        self.df["observation_full_id"] = "urn:uuid:" + self.df["observation_id"] 
        # print("this is the data: ", self.df)
        if self.addPrefix:
            self.df = self.df.add_prefix("resource_")
        self.df = self.df.fillna("nan")
        features_for_table = {
            "strings" : [],
            "categorical" : [],
            "timestamps" : [],
            "numeric"   :[]
        }
        valid_num_columns = [col for col in self.numeric_variables if col in self.df.columns]
        valid_str_columns = [col for col in self.string_variables if col in self.df.columns]

        features_for_table["strings"] = list(map(lambda x: StringVariable(name=x), valid_str_columns))
        features_for_table["numeric"] = list(map(lambda x: ContinuousVariable(name=x), valid_num_columns))

        features_for_table["categorical"] = self.make_cat_variables()
        domain = Domain(features_for_table["numeric"] + features_for_table["categorical"] , metas = features_for_table["strings"])
        
        return domain


    def extract_Observations(self, path=None,res_from_request=None):
        
        if path is not None:
            with open(path,"r") as f:
                bundle_data = json.load(f)
                f.close()   
        else:
            bundle_data = res_from_request
        try:
            patient_resources  = bundle_data["entry"]
            idx_res = map(lambda resource: resource["resource"]["resourceType"] == "Observation", patient_resources) 
            list_observations = [element for element, is_observation in zip(patient_resources, idx_res) if is_observation]
        except KeyError:
            self.addPrefix = True
            list_observations = [element for element in [bundle_data]]
        
        return list_observations
    
    
        
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
                
                medication_requests = self.extract_Observations(path)
                processed_resources = list(map(self.flatten_dict, medication_requests))
                [self.all_res.append(resource) for resource in processed_resources]
            self.create_table()

        
if __name__ == "__main__":
    widgetpreview.WidgetPreview(OWFhirImportObservation).run()


