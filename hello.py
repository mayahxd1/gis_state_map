from flask import Flask, jsonify, request
import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Database connection
DATABASE_URL = "postgresql://postgres:2806@localhost/my_spatial_db"
engine = create_engine(DATABASE_URL)

@app.route('/')
def home():
    return 'Flask is running!'



@app.route('/state/<state_name>')
def get_state(state_name):
    print(f"Received state name: {state_name}")
    # Convert state_name to string and clean it
    state_name = str(state_name).strip()
    state_abbr = state_name.upper()
    # Query for specific state using indexes on name and stusps columns
    query = text("""
    SELECT * FROM public.states
    WHERE LOWER(name) = LOWER(:state_name) OR UPPER(stusps) = UPPER(:state_abbr)
    LIMIT 1
    """)

    try:
        with engine.connect() as conn:
            df = gpd.read_postgis(
                query,
                conn,
                params={"state_name": state_name, "state_abbr": state_abbr},
                geom_col="geom"
            )

        # Load population data
        pop_df = pd.read_csv("state_population.csv")

        # Normalize casing for state names
        pop_df['name'] = pop_df['name'].str.strip().str.lower()
        df["name"] = df["name"].str.strip().str.lower()

        # Merge population info into spatial geodataframe
        df = df.merge(pop_df, on="name", how="left")

        # Print the dataframe
        print(f"Query results for {state_name}:")
        print(df)

        if df.empty:
            return jsonify({
                "error": f"No data found for state: {state_name}"
            }), 404

        # Convert to GeoJSON and enable CORS
        response = jsonify(df.to_json())
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        # Enable CORS on error response
        response = jsonify({
            "error": f"Error retrieving state data: {str(e)}"
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 500

@app.route('/compare')
def compare_states():
    state1 = request.args.get('state1')
    state2 = request.args.get('state2')

    if not state1 or not state2:
        return jsonify({"error": "Both state1 and state2 parameters are required."}), 400

    # Convert state names to lowercase for comparison
    state1 = state1.strip().lower()
    state2 = state2.strip().lower()

    # Query for both states using indexes on name or stusps columns
    query = text("""
        SELECT DISTINCT ON (name) *  FROM public.states
        WHERE LOWER(name) IN (LOWER(:state1), LOWER(:state2)) OR UPPER(stusps) IN (UPPER(:state1), UPPER(:state2))
        """)

    try:
        with engine.connect() as conn:
            df = gpd.read_postgis(
                query,
                conn,
                params={
                    "state1": state1, "state2": state2,
                    "state1_abbr": state1.upper(), "state2_abbr": state2.upper()
                },
                geom_col="geom"
            )

        # Load population data
        pop_df = pd.read_csv("state_population.csv")
        # Normalize casing for state names
        pop_df['name'] = pop_df['name'].str.strip().str.lower()
        df["name"] = df["name"].str.strip().str.lower()
        # Merge population info into spatial geodataframe
        df = df.merge(pop_df, on="name", how="left")

        #Drop geometry column for comparison - just return the data
        df = df.drop(columns="geom")

        return jsonify(df.to_dict(orient="records"))

    except Exception as e:
        return jsonify({"error": f"Error comparing states: {str(e)}"}), 500


@app.route('/dropdown')
def get_dropdown():
    query = text("SELECT DISTINCT name FROM public.states ORDER BY name")
    with engine.connect() as conn:
        result = conn.execute(query)
        states = [row[0] for row in result]
    return jsonify(states)

if __name__ == '__main__':
    app.run(debug=True)