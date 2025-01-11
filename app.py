from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd
import os
import requests
import uuid


app = Flask(__name__)

from dotenv import load_dotenv

load_dotenv()

from authlib.integrations.flask_client import OAuth
from flask import Flask, redirect, url_for, session

app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Configure GitHub OAuth
oauth = OAuth(app)
github = oauth.register(
    name='github',
    client_id=os.getenv('GITHUB_CLIENT_ID'),
    client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'}
)

@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return github.authorize_redirect(redirect_uri)


@app.route('/callback')
def authorize():
    token = github.authorize_access_token()
    user_info = github.get('user').json()
    user_email = github.get('user/emails').json()

    # Store user info in session
    session['user'] = {
        'username': user_info['login'],
        'email': user_email[0]['email'] if user_email else 'No public email',
    }

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Initialize the dataset
if not os.path.exists("dataset.csv"):
    df = pd.DataFrame(columns=["KE_ID", "WP_ID", "Timestamp"])
    df.to_csv("dataset.csv", index=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/explore')
def explore():
    # print("Session User Info:", session.get('user')) 
    user_info = session.get('user', {})
    df = pd.read_csv("dataset.csv")
    data = df.to_dict(orient="records")
    return render_template("explore.html", dataset=data, user_info=user_info)



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
    if not pair_match.empty:
        return jsonify({
            "pair_exists": True,
            "message": f"The KE-WP pair ({ke_id}, {wp_id}) already exists."
        }), 200

    # Check for existing KE ID
    ke_match = df[df["KE_ID"] == ke_id]
    if not ke_match.empty:
        return jsonify({
            "ke_exists": True,
            "message": f"The KE ID {ke_id} exists but not with WP ID {wp_id}.",
            "ke_matches": ke_match.to_dict(orient="records")
        }), 200

    # Neither the pair nor KE exists
    return jsonify({
        "ke_exists": False,
        "pair_exists": False,
        "message": f"The KE ID {ke_id} and WP ID {wp_id} are new entries."
    }), 200


@app.route('/submit', methods=['POST'])
def submit():
    """Add a new KE-WP mapping entry to the dataset."""
    ke_id = request.form.get('ke_id')
    wp_id = request.form.get('wp_id')
    ke_title = request.form.get('ke_title')  # Get KE title
    wp_title = request.form.get('wp_title')  # Get WP title
    connection_type = request.form.get("connection_type", "undefined")
    confidence_level = request.form.get("confidence_level", "low")

    if not ke_id or not wp_id or not ke_title or not wp_title:
        return jsonify({"error": "All fields are required."}), 400

    # Load the dataset
    df = pd.read_csv("dataset.csv")

    # Prevent duplicate KE-WP pair entries
    if not df[(df["KE_ID"] == ke_id) & (df["WP_ID"] == wp_id)].empty:
        return jsonify({
            "error": "The KE-WP pair already exists in the dataset."
        }), 400

    # Add new entry
    new_entry = {
        "KE_ID": ke_id,
        "KE_Title": ke_title,  # Include KE title
        "WP_ID": wp_id,
        "WP_Title": wp_title,  # Include WP title
        "Connection_Type": connection_type,
        "Confidence_Level": confidence_level,
        "Timestamp": pd.Timestamp.now()
    }
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
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
        # print("SPARQL Response:", response.json())
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
        # print("SPARQL Pathway Response:", response.json())  # Debugging log
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

@app.route('/submit_proposal', methods=['POST'])
@login_required
def submit_proposal():
    """Save user proposals as text files with the date included."""
    entry = request.form.get('entry')
    user_name = request.form.get('userName')
    user_email = request.form.get('userEmail')
    user_affiliation = request.form.get('userAffiliation')
    proposed_changes = {
        "delete": request.form.get('proposedChanges[delete]') == "true",
        "confidence": request.form.get('proposedChanges[confidence]'),
        "type": request.form.get('proposedChanges[type]')
    }

    if not all([entry, user_name, user_email, user_affiliation]):
        return jsonify({"error": "All fields are required."}), 400

    # Create a directory to store proposals
    proposals_dir = "proposals"
    os.makedirs(proposals_dir, exist_ok=True)

    # Generate a filename with the date included
    date_str = pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M-%S')
    proposal_file = os.path.join(proposals_dir, f"proposal_{date_str}.txt")

    # Save proposal details to the text file
    with open(proposal_file, "w") as f:
        f.write(f"Date: {date_str}\n")
        f.write(f"User Name: {user_name}\n")
        f.write(f"User Email: {user_email}\n")
        f.write(f"User Affiliation: {user_affiliation}\n")
        f.write(f"Selected Entry: {entry}\n")
        f.write(f"Proposed Changes:\n")
        f.write(f"  Delete: {proposed_changes['delete']}\n")
        f.write(f"  Confidence: {proposed_changes['confidence']}\n")
        f.write(f"  Type: {proposed_changes['type']}\n")

    return jsonify({"message": "Proposal saved successfully."}), 200


if __name__ == '__main__':
    app.run(debug=True)
