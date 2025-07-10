from setuptools import setup, find_packages

setup(
    name="orange_widgets",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "Orange3==3.37.0",
        "pandas",
        "numpy",
        "openai==1.23.6",
        "matplotlib",
        "PyQt5",
        "pySankey",
        "scikit-learn" ,
        "plotly",
        "seaborn"
    ],
    include_package_data=True,
    entry_points={
        'orange3.addon': (
            'orange_widgets = orange_widgets',
        ),
        'orange.widgets': (
            'FHIR Widgets = orange_widgets',
        ),
    },
    author="Emanuele Damiano",
    description="Orange widgets for handling FHIR data",
    license="MIT",
)
