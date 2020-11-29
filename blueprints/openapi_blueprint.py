"""
This module contains the opeanAPI3 spec root endpoint as a Flask Blueprints
"""
import json
from flask import Blueprint
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin

openapi = Blueprint("openapi", __name__)

# Declare shell colour variables for logging output
OKBLUE = "\033[94m"
OKGREEN = "\033[92m"
WARNING = "\033[93m"
FAIL = "\033[91m"
ENDC = "\033[0m"

###########################
##### API SPEC ############
# API spec is autogenerated using the 'api-spec' library, and saved in the project root
# as well as being served on the root '/' endpoint for consumption by services
spec = APISpec(
    title="RCPCH Digital Growth Charts API",
    version="0.0.3",
    openapi_version="3.0.2",
    info=dict(
        description="Royal College of Paediatrics and Child Health Digital Growth Charts",
        license={"name": "GNU Affero General Public License",
                 "url": "https://www.gnu.org/licenses/agpl-3.0.en.html"}),
    plugins=[MarshmallowPlugin(), FlaskPlugin()],
    servers=[{"url": 'https://api.rcpch.ac.uk/',
              "description": 'RCPCH Production API Gateway'},
             {"url": 'https://localhost:5000/',
              "description": 'Your local development API'}],
)


# Create JSON OpenAPI Spec and serve it at /
@openapi.route("/", methods=["GET"])
def openapi_endpoint():
    """
    openAPI3.0 Specification.
    ---
    get:
      summary: openAPI3.0 Specification.
      description: |
        * The root endpoint of the Digital Growth Charts API returns the openAPI3.0 specification in JSON format.
        * This can be used to autogenerate client scaffolding and tests.
        * We use it internally to generate all documentation, Postman collections and tests.
        * The openAPI specification is also available in YAML form, in the root of the Server codebase at https://github.com/rcpch/digital-growth-charts-server

      responses:
        200:
          description: |
            * openAPI3.0 Specification in JSON format, conforming to https://swagger.io/specification/, is returned.
          content:
            application/json:
              schema: OpenApiSchema
    """
    return json.dumps(spec.to_dict()), 200


################################
### API SPEC AUTO GENERATION ###

# Create YAML OpenAPI Spec and serialise it to file
try:
    with open(r'openapi.yaml', 'w') as file:
        openapi_spec = file.write(spec.to_yaml())
        print(f"{OKGREEN} * openAPI3.0 spec was generated and saved to the repo{ENDC}")

except:
    print(f"{FAIL} * An error occurred while processing the openAPI3.0 spec{ENDC}")

### END API SPEC AUTO GENERATION ###
####################################