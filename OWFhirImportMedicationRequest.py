from Orange.data import Domain, StringVariable, DiscreteVariable, ContinuousVariable, Table
from Orange.widgets import widget, gui
from Orange.widgets.utils.signals import Input, Output
from tkinter import filedialog
import json
from Orange.widgets.utils import widgetpreview
import re 
import requests
import pandas as pd 

class OWFhirAnalyzieMedicationRequest(widget.OWWidget):
    name = "Import Medication Requests"
    description = "returns processed orange table for medication request FHIR resource"
    category = "FHIR Widgets"
    icon = "icons/medication_icon.png"

    class Inputs:
        list_of_paths = widget.Input("Bundle Resource Paths", list)

    class Outputs:
        processed_table = widget.Output("Processed MedicationRequest Table", Table)


    def __init__(self):
        super().__init__()
        
        self.string_variables = ["MedicationRequest_id", "MedicationRequest_medicationCodeableConcept_text", "MedicationRequest_subject_reference",
                                 "MedicationRequest_encounter_reference","MedicationRequest_authoredOn",
                                "MedicationRequest_reasonReference_0_reference"]
        self.numeric_variables = ["MedicationRequest_dosageInstruction_0_timing_repeat_frequency", "MedicationRequest_dosageInstruction_0_sequence",
                                    "MedicationRequest_dosageInstruction_0_timing_repeat_period",
                                    "MedicationRequest_dosageInstruction_0_doseAndRate_0_doseQuantity_value"]
        self.cat_variables = ["MedicationRequest_status", "MedicationRequest_intent", "MedicationRequest_medicationCodeableConcept_coding_0_code",
                              "MedicationRequest_medicationCodeableConcept_coding_0_display","MedicationRequest_requester_display",
                            "MedicationRequest_dosageInstruction_0_timing_repeat_periodUnit","MedicationRequest_dosageInstruction_0_asNeededBoolean",
                            "MedicationRequest_dosageInstruction_0_doseAndRate_0_type_coding_0_code",
                            "MedicationRequest_dosageInstruction_0_additionalInstruction_0_coding_0_display","reason_0_concept_coding_0_display"]
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
        self.upload_button = gui.button(box2, self, label="Import one or more medication request resources", callback=self.selectMedicationRequests)
    
        gui.separator(self)
        


    def selectMedicationRequests(self):
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
        
        self.df.columns = self.df.columns.str.replace(r'^resource_', 'MedicationRequest_', regex=True)


        if self.addPrefix:
            self.df = self.df.add_prefix("MedicationRequest_")
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
        
        domain = Domain(features_for_table["numeric"]+ features_for_table["categorical"] , metas = features_for_table["strings"])
        return domain


    def extract_MedicationRequest(self, path=None,res_from_request=None):
        
        if path is not None:
            with open(path,"r") as f:
                bundle_data = json.load(f)
                f.close()   
        else:
            bundle_data = res_from_request
        try:
            patient_resources  = bundle_data["entry"]
            idx_med_req = map(lambda resource: resource["resource"]["resourceType"] == "MedicationRequest", patient_resources) 
            list_med_request = [element for element, ismedicationreq in zip(patient_resources, idx_med_req) if ismedicationreq]
        except KeyError:
            ## this case means that we are operating with only one medication request set of data and not a bundle of resources
            ## so we add a prefix for having the same format 
            self.addPrefix = True
            list_med_request = [element for element in [bundle_data]]
        
        return list_med_request
    
    
        
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
                
                medication_requests = self.extract_MedicationRequest(path)
                processed_resources = list(map(self.flatten_dict, medication_requests))
                [self.all_res.append(resource) for resource in processed_resources]
            self.create_table()

        
if __name__ == "__main__":
    widgetpreview.WidgetPreview(OWFhirAnalyzieMedicationRequest).run()


