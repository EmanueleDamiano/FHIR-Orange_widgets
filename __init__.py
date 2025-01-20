# # __init__.py
# from .OWAI_widget_full import OWAIWidget_Full
# # from .another_widget import AnotherWidget

# # Optionally, you can include other imports as needed

# # If you have a specific category for your widgets
# from Orange.widgets import widget
# # Registering the widgets with Orange
# widget.registry.register(OWAIWidget_Full)
# # widget.registry.register(AnotherWidget)

# # Optionally, you can also expose icons or resources if needed
# # This could help if you want to have a centralized way to reference your icons
# def get_icon(icon_name):
#     """Return the path for the specified icon."""
#     return f"icons/{icon_name}"

# # Example usage
# # You can use `get_icon('my_icon.png')` in your widget classes to get the icon path

# __all__ = [
#     "OWAIWidget_Full",
#     "get_icon",  # Expose the get_icon function if needed
# ]
