from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd
import os
import requests

app = Flask(__name__)

# Initialize the dataset
if not os.path.exists("dataset.csv"):
    df = pd.DataFrame(columns=["KE_ID", "WP_ID", "Timestamp"])
    df.to_csv("dataset.csv", index=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/explore')
def explore():
    # Load the dataset
    df = pd.read_csv("dataset.csv")
    data = df.to_dict(orient="records")
    return render_template("explore.html", dataset=data)

# Ensure dataset exists
if not os.path.exists("dataset.csv"):
    pd.DataFrame(columns=["KE_ID", "WP_ID", "Timestamp"]).to_csv("dataset.csv", index=False)

@app.route('/check', methods=['POST'])
def check_entry():
    """Check if the KE ID or the KE-WP pair already exist in the dataset."""
    ke_id = request.form.get('ke_id')
    wp_id = request.form.get('wp_id')

    if not ke_id or not wp_id:
        return jsonify({"error": "Both KE ID and WP ID are required."}), 400

    # Load the dataset
    df = pd.read_csv("dataset.csv")

    # Check for exact KE-WP pair
    pair_match = df[(df["KE_ID"] == ke_id) & (df["WP_ID"] == wp_id)]

    # Check for existing KE ID
    ke_match = df[df["KE_ID"] == ke_id]

    if not pair_match.empty:
        # If the exact pair exists, no need to add
        return jsonify({
            "pair_exists": True,
            "pair_match": pair_match.iloc[0].to_dict()
        }), 200

    if not ke_match.empty:
        # If only KE exists, user should confirm
        return jsonify({
            "ke_exists": True,
            "ke_matches": ke_match.to_dict(orient="records")
        }), 200

    # Neither the pair nor KE exists
    return jsonify({"ke_exists": False, "pair_exists": False}), 200

@app.route('/submit', methods=['POST'])
def submit():
    """Add a new KE-WP mapping entry to the dataset."""
    ke_id = request.form.get('ke_id')
    ke_title = request.form.get('ke_title')
    wp_id = request.form.get('wp_id')
    wp_title = request.form.get('wp_title')

    if not ke_id or not ke_title or not wp_id or not wp_title:
        return jsonify({"error": "All fields (KE ID, KE Title, WP ID, WP Title) are required."}), 400

    # Load the dataset
    df = pd.read_csv("dataset.csv")

    # Add the new entry
    new_entry = {
        "KE_ID": ke_id,
        "KE_Title": ke_title,
        "WP_ID": wp_id,
        "WP_Title": wp_title,
        "Timestamp": pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')  # Exclude milliseconds
    }
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)

    # Save back to the CSV
    df.to_csv("dataset.csv", index=False)

    return jsonify({"message": "Entry added successfully."}), 200




@app.route('/get_ke_options', methods=['GET'])
def get_ke_options():
    sparql_query = """
    PREFIX aopo: <http://aopkb.org/aop_ontology#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>

    SELECT ?KEtitle ?KElabel ?KEpage
    WHERE {
      ?KE a aopo:KeyEvent ; 
          dc:title ?KEtitle ; 
          rdfs:label ?KElabel; 
          foaf:page ?KEpage. 
    }
    """
    endpoint = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql"
    response = requests.post(
        endpoint,
        data={"query": sparql_query},
        headers={"Accept": "application/json"}
    )
    if response.status_code == 200:
        # Log raw response for debugging
        print("SPARQL Response:", response.json())
        data = response.json()
        results = [
            {
                "KEtitle": binding.get("KEtitle", {}).get("value", ""),
                "KElabel": binding.get("KElabel", {}).get("value", ""),
                "KEpage": binding.get("KEpage", {}).get("value", "")
            }
            for binding in data["results"]["bindings"]
        ]
        return jsonify(results), 200
    else:
        print("SPARQL Query Failed:", response.text)
        return jsonify({"error": "Failed to fetch KE options"}), 500

@app.route('/get_pathway_options', methods=['GET'])
def get_pathway_options():
    """Fetch pathway options from the SPARQL endpoint."""
    sparql_query = """
    PREFIX wp: <http://vocabularies.wikipathways.org/wp#>
    PREFIX dc: <http://purl.org/dc/elements/1.1/>
    PREFIX dcterms: <http://purl.org/dc/terms/>

    SELECT DISTINCT ?pathwayID ?pathwayTitle ?pathwayLink
    WHERE {
        ?pathwayRev a wp:Pathway ; 
                    dc:title ?pathwayTitle ; 
                    dc:identifier ?pathwayLink ; 
                    dcterms:identifier ?pathwayID ;
                    wp:organismName "Homo sapiens" .
    }
    """
    endpoint = "https://sparql.wikipathways.org/sparql"
    response = requests.post(
        endpoint,
        data={"query": sparql_query},
        headers={"Accept": "application/json"}
    )
    if response.status_code == 200:
        print("SPARQL Pathway Response:", response.json())  # Debugging log
        data = response.json()
        results = [
            {
                "pathwayID": binding.get("pathwayID", {}).get("value", ""),
                "pathwayTitle": binding.get("pathwayTitle", {}).get("value", ""),
                "pathwayLink": binding.get("pathwayLink", {}).get("value", "")
            }
            for binding in data["results"]["bindings"]
        ]
        return jsonify(results), 200
    else:
        print("SPARQL Pathway Query Failed:", response.text)  # Debugging log
        return jsonify({"error": "Failed to fetch pathway options"}), 500


@app.route('/download')
def download():
    return send_file("dataset.csv", as_attachment=True)

@app.route('/ke-details')
def ke_details():
    return render_template('ke-details.html')

@app.route('/pw-details')
def pw_details():
    return render_template('pw-details.html')



if __name__ == '__main__':
    app.run(debug=True)