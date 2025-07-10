from Orange.widgets import widget, gui
from Orange.widgets.utils.signals import Output
from tkinter import filedialog
from Orange.widgets.utils import widgetpreview


class OWFhirLoading(widget.OWWidget):
    name = "PathLoading"
    description = "Select FHIR resources path from your local system"
    category = "FHIR Widgets"
    want_main_area = True
    icon = "icons/pathloading_icon.png"
    
    class Outputs:
        list_of_paths = Output("Bundle Resource Paths", list)
        print(list_of_paths)
        
    def __init__(self):
        super().__init__()



        self.box = gui.widgetBox(self.mainArea,"Upload Files")
        self.box.setFixedHeight(100)
        self.upload_button = gui.button(self.box, self, label="Import one or more JSON files", callback=self.upload_action)
        
        
    def upload_action(self):
        file_paths = filedialog.askopenfilenames(title="Select JSON file(s)", filetypes=(("JSON files", "*.json"),))
        if file_paths:
            self.commit(file_paths)
        else:
            self.display_message = gui.widgetLabel(self.box,"NO FILE SELECTED ")

    def commit(self,file_paths):
        self.Outputs.list_of_paths.send(file_paths)

        

        
# if __name__ == "__main__":
#     widgetpreview.WidgetPreview(OWFhirLoading).run()
