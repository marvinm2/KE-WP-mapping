# KE-WP Mapping Application

This is a Flask-based web application for mapping Key Events (KEs) to WikiPathways (WPs) with additional metadata like connection types and confidence levels. The application supports user authentication using GitHub OAuth, ensuring secure interactions and user-specific functionalities.

## Features

- **Map Key Events to WikiPathways:**
  Users can select Key Events and WikiPathways, define the connection type, and specify the confidence level for the mapping.

- **Data Exploration:**
  A searchable and sortable table of existing mappings with metadata.

- **Proposal Submission:**
  Users can propose changes to mappings, such as updating connection types, confidence levels, or deleting mappings.

- **GitHub Authentication:**
  Secure login using GitHub OAuth to restrict certain actions (e.g., submitting proposals) to authenticated users.

- **CSV Export:**
  Download the dataset as a CSV file for offline analysis.

## Technologies Used

- **Backend:** Flask
- **Frontend:** HTML, CSS, JavaScript (jQuery, DataTables)
- **Database:** CSV (for simplicity; scalable to other databases)
- **Authentication:** GitHub OAuth (via `authlib` library)
- **SPARQL Queries:** Used to fetch Key Event and WikiPathway details from respective endpoints.

## Installation

### Prerequisites

- Python 3.7 or higher
- `pip` (Python package manager)

### Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/your-repo/ke-wp-mapping.git
   cd ke-wp-mapping
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables for GitHub OAuth:
   - Create a `.env` file in the project root:
     ```plaintext
     GITHUB_CLIENT_ID=your_client_id
     GITHUB_CLIENT_SECRET=your_client_secret
     FLASK_SECRET_KEY=your_flask_secret_key
     ```

5. Run the application:
   ```bash
   flask run
   ```

6. Access the app at [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Usage

### Key Event and Pathway Mapping
1. Log in using your GitHub account.
2. Select a Key Event and WikiPathway from the dropdown menus.
3. Specify the connection type and confidence level.
4. Submit the mapping.

### Explore Existing Mappings
- Visit the **Explore Dataset** page to view all mappings in a searchable and sortable table.

### Propose Changes
- Click the **Propose Change** button on any mapping to suggest updates. Only logged-in users can submit proposals.

## SPARQL Endpoints

- **Key Events:** [AOP-Wiki SPARQL](https://aopwiki.rdf.bigcat-bioinformatics.org/sparql)
- **WikiPathways:** [WikiPathways SPARQL](https://sparql.wikipathways.org/sparql)

## Contributing

Contributions are welcome! Please fork this repository, create a feature branch, and submit a pull request, or simply file an issue.

## Acknowledgments

- Data fetched using SPARQL endpoints from AOP-Wiki and WikiPathways.
- Authentication powered by GitHub OAuth.

## Contact

For any questions or issues, please contact [marvin.martens@maastrichtuniversity.nl].

