"""
RCPCH Growth Charts API Server
"""

import json
from datetime import datetime
from os import environ, urandom

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask import Flask, jsonify, request
from flask_cors import CORS
import blueprints
import controllers
from schemas import (SingleCalculationResponseSchema, MultipleCalculationsResponseSchema,
                     ReferencesResponseSchema, FictionalChildResponseSchema, ChartDataResponseSchema)


#######################
##### FLASK SETUP #####
app = Flask(__name__, static_folder="static")
CORS(app)
app.register_blueprint(
    blueprints.utilities_blueprint.utilities, url_prefix='/utilities')

# Declare shell colour variables for logging output
OKBLUE = "\033[94m"
OKGREEN = "\033[92m"
WARNING = "\033[93m"
FAIL = "\033[91m"
ENDC = "\033[0m"

# ENVIRONMENT
# Load the secret key from the ENV if it has been set
if "FLASK_SECRET_KEY" in environ:
    app.secret_key = environ["FLASK_SECRET_KEY"]
    print(f"{OKGREEN} * FLASK_SECRET_KEY was loaded from the environment{ENDC}")
# Otherwise create a new one. (NB: We don't need session persistence between reboots of the app)
else:
    app.secret_key = urandom(16)
    print(f"{OKGREEN} * A new SECRET_KEY for Flask was automatically generated{ENDC}")

from app import app     # position of this import is important. Don't allow it to be autoformatted alphabetically to the top of the imports!

##### END FLASK SETUP #####
###########################

###########################
##### API SPEC ############
# API spec is autogenerated using the 'api-spec' library, and saved in the project root
# as well as being served on the root '/' endpoint for consumption by services
spec = APISpec(
    title="RCPCH Digital Growth Charts API Server",
    version="0.0.3",
    openapi_version="3.0.2",
    info=dict(
        description="Royal College of Paediatrics and Child Health Digital Growth Charts API Server",
        license={"name": "GNU Affero General Public License",
                 "url": "https://www.gnu.org/licenses/agpl-3.0.en.html"}),
    plugins=[MarshmallowPlugin(), FlaskPlugin()],
    servers=[{"url": 'https://api.rcpch.ac.uk/',
              "description": 'RCPCH Production API Gateway'},
             {"url": 'https://localhost:5000/',
              "description": 'Your local development API'}],
)
##### END API SPEC ########
###########################


# JSON CALCULATION OF MULTIPLE MEASUREMENT METHODS AT SAME TIME
# USED BY THE FLASK DEMO CLIENT
@app.route("/uk-who/calculations", methods=["POST"])
def uk_who_calculations():
    """Multiple Calculations API route.
    ---
    post:
      summary: |-
        Calculates *multiple* digital growth chart parameters.
        Returns centiles for height, weight, BMI and OFC when supplied the required input values.

      requestBody:
        content:
          application/json:
            schema: MultipleCalculationsRequestParameters

      responses:
        200:
          description: "Centile calculations corresponding to the supplied data"
          content:
            application/json:
              schema: MultipleCalculationsResponseSchema
    """
    if request.is_json:
        req = request.get_json()
        response = controllers.perform_calculations(
            birth_date=datetime.strptime(req["birth_date"], "%Y-%m-%d"),
            observation_date=datetime.strptime(
                req["observation_date"], "%Y-%m-%d"),
            height=float(req["height_in_cm"]),
            weight=float(req["weight_in_kg"]),
            ofc=float(req["head_circ_in_cm"]),
            sex=str(req["sex"]),
            gestation_weeks=int(req["gestation_weeks"]),
            gestation_days=int(req["gestation_days"])
        )
        return jsonify(response), 200
    else:
        return "Request body mimetype should be application/json", 400


spec.components.schema(
    "calculations", schema=MultipleCalculationsResponseSchema)
with app.test_request_context():
    spec.path(view=uk_who_calculations)


@app.route("/uk-who/calculation", methods=["POST"])
def uk_who_calculation():
    """Single Calculations API route.
    ---
    post:
      summary: |
        Calculates *single* digital growth chart parameters.
        Returns a single calculation for the selected `measurement_method`.
        Available `measurement_method`s are: `height`, `weight`, `bmi`, or `ofc` (OFC = occipitofrontal circumference = 'head circumference').
        Note that BMI must be precalculated for the `bmi` function.

      requestBody:
        content:
          application/json:
            schema: SingleCalculationRequestParameters

      responses:
        200:
          description: "Centile calculation (single) according to the supplied data"
          content:
            application/json:
              schema: SingleCalculationResponseSchema
    """
    if request.is_json:
        req = request.get_json()
        calculation = controllers.perform_calculation(
            birth_date=datetime.strptime(req["birth_date"], "%Y-%m-%d"),
            observation_date=datetime.strptime(
                req["observation_date"], "%Y-%m-%d"),
            measurement_method=str(req["measurement_method"]),
            observation_value=float(req["observation_value"]),
            sex=str(req["sex"]),
            gestation_weeks=int(req["gestation_weeks"]),
            gestation_days=int(req["gestation_days"])
        )
        return jsonify(calculation)
    else:
        return "Request body mimetype should be application/json", 400

spec.components.schema("calculation", schema=SingleCalculationResponseSchema)
with app.test_request_context():
    spec.path(view=uk_who_calculation)


@app.route("/uk-who/chart-data", methods=["POST"])
def uk_who_chart_data():
    """
    Chart data API route.
    ---
    post:
      summary: |
        Chart data API route.
        Requires results data paramaters from a call to the calculation endpoint.
        Returns geometry data for constructing the lines of a traditional growth chart.

      requestBody:
        content:
          application/json:
            schema: ChartDataRequestParameters

      responses:
        200:
          description: "Chart data for plotting a traditional growth chart"
          content:
            application/json:
              schema: ChartDataResponseSchema
    """
    if request.is_json:
        req = request.get_json()
        results = req["results"]
        unique_child = req["unique_child"]
        # born preterm flag to pass to charts
        born_preterm = (results[0]["birth_data"]["gestation_weeks"]
                        != 0 and results[0]["birth_data"]["gestation_weeks"] < 37)
        if unique_child == "true":
            # data are serial data points for a single child
            # Prepare data from plotting
            child_data = controllers.create_data_plots(results)
            # Retrieve sex of child to select correct centile charts
            sex = results[0]["birth_data"]["sex"]
        else:
            # if unique_child = False then the series of calculations are from different children
            # Prepare data from plotting
            child_data = controllers.create_data_plots(results)
            # Retrieve sex of child to select correct centile charts
            sex = results[0]["birth_data"]["sex"]
        # Create Centile Charts
        centiles = controllers.create_centile_values(
            sex, born_preterm=born_preterm)
        return jsonify({
            "sex": sex,
            "child_data": child_data,
            "centile_data": centiles
        })
    else:
        return "Request body should be application/json", 400


spec.components.schema("chartData", schema=ChartDataResponseSchema)
with app.test_request_context():
    spec.path(view=uk_who_chart_data)


@app.route("/uk-who/spreadsheet", methods=["POST"])
def ukwho_spreadsheet():
    """
    ***INCOMPLETE***
    Spreadsheet file upload API route.
    ---
    post:
      summary: |
        Spreadsheet file upload API route.
        This endpoint is used for development and testing only and it is not envisaged that it will be in the live API

      requestBody:
        content:
          text/csv:
            schema: ChartDataRequestParameters

      responses:
        200:
          description: "Chart data for plotting a traditional growth chart"
          content:
            application/json:
              schema: ChartDataResponseSchema
    """
    csv_file = request.files["csv_file"]
    calculated_results = controllers.import_csv_file(csv_file)
    return calculated_results


### Utilities refactored out into Blueprints ###
spec.components.schema("references", schema=ReferencesResponseSchema)
with app.test_request_context():
    spec.path(view=blueprints.references)

spec.components.schema("fictionalChild", schema=FictionalChildResponseSchema)
with app.test_request_context():
    spec.path(view=blueprints.create_fictional_child_measurements)

with app.test_request_context():
    spec.path(view=blueprints.instructions)


################################
### API SPEC AUTO GENERATION ###

# Create JSON OpenAPI Spec and serve it at /
@app.route("/", methods=["GET"])
def apispec():
    return json.dumps(spec.to_dict())


# Create YAML OpenAPI Spec and serialise it to file
try:
    with open(r'openapi.yaml', 'w') as file:
        openapi_spec = file.write(spec.to_yaml())
        print(f"{OKGREEN} * openAPI3.0 spec was generated and saved to the repo{ENDC}")

except:
    print(f"{FAIL} * An error occurred while processing the openAPI3.0 spec{ENDC}")

### END API SPEC AUTO GENERATION ###
####################################


if __name__ == "__main__":
    app.run()
