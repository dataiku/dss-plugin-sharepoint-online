PLUGIN_VERSION=1.0.3
PLUGIN_ID=sharepoint-online

plugin:
	cat plugin.json|json_pp > /dev/null
	rm -rf dist
	mkdir dist
	zip --exclude "*.pyc" -r dist/dss-plugin-${PLUGIN_ID}-${PLUGIN_VERSION}.zip code-env parameter-sets plugin.json python-connectors python-fs-providers python-lib
