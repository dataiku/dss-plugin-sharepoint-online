from sharepoint_client import SharePointClient


def do(payload, config, plugin_config, inputs):
    print("ALX:do:config={}".format(config))
    print("ALX:do:plugin_config={}".format(plugin_config))
    print("ALX:do:inputs={}".format(inputs))

    if "config" in config:
        print("ALX:do:config in config")
        config = config.get("config")
        print("ALX:do:config in config2")
    print("ALX:do:before advanced")
    advanced_parameters = config.get("advanced_parameters", False)
    print("ALX:do:advanced_parameters={}".format(advanced_parameters))
    if not advanced_parameters:
        print("ALX:do:not advanced")
        return {"choices": []}
    if "sharepoint_oauth" not in config:
        print("ALX:do:sharepoint_oauth not in config {}".format(config))
        return {"choices": [{"label": "Requires DSS v1.0.3 or above."}]}
    elif config.get("sharepoint_oauth") == {}:
        print("ALX:do:sharepoint_oauth empty {}".format(config))
        return {"choices": [{"label": "Pick a credential"}]}

    print("ALX:do:before client")
    client = SharePointClient(config)
    print("ALX:do:after client")

    parameter_name = payload.get("parameterName")
    print("ALX:do:parameter_name={}".format(parameter_name))

    if parameter_name == "sharepoint_site_select":
        print("ALX:do:parameter_name")
        choices = client.get_available_site_paths()
        print("ALX:do:choices={}".format(choices))
        return {"choices": choices}
