
This repository provides a custom widget set for integrating FHIR resources into the [Orange Data Mining](https://orangedatamining.com/) environment. 
The widgets support drag-and-drop operations for building pipelines on a visual canvas.

## Installation instructions
Before executing these instructions please ensure that both Python and Orange are installed on your local system. 
1. Clone this repository locally. 
```bash 
    git clone https://github.com/EmanueleDamiano/FHIR-Orange_widgets 
``` 
2. Navigate to the cloned repository and execute the following command. This will create a file named 'orange_custom_widgets-0.1.tar.gz' necessary for the installation.
```
    python setup.py sdist
```
3. The installation is completed by using in the same directory:
```
    pip install dist/orange_custom_widgets-0.1.tar.gz
```
4. Finally Orange can be started using:
```
    python -m Orange.canvas
```

The installed widget will appear on the left hand side of the Orange canvas in the 'FHIR Widgets' category. 

Each API request has a small cost. For this proof of concept, the user is required to get its own key from https://console.apillm.com/pt/auth/login as it is currently the only api service supported.  
