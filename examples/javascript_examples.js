/**
 * JavaScript Examples for KE-WP Mapping Dataset
 * Demonstrates frontend integration, API usage, and data visualization
 */

class KEWPDatasetClient {
    constructor(baseUrl = 'https://ke-wp-mapping.org') {
        this.baseUrl = baseUrl.replace(/\/$/, '');
    }

    async makeRequest(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }

        return response;
    }

    async getMappings(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const endpoint = `/api/v1/mappings${queryString ? `?${queryString}` : ''}`;
        const response = await this.makeRequest(endpoint);
        return response.json();
    }

    async getMapping(mappingId) {
        const response = await this.makeRequest(`/api/v1/mappings/${mappingId}`);
        return response.json();
    }

    async searchMappings(query, params = {}) {
        return this.getMappings({ search: query, ...params });
    }

    async getStatistics() {
        const response = await this.makeRequest('/api/v1/mappings/stats');
        return response.json();
    }

    async exportData(format, options = {}) {
        const queryString = new URLSearchParams(options).toString();
        const endpoint = `/export/${format}${queryString ? `?${queryString}` : ''}`;
        return this.makeRequest(endpoint);
    }

    async getAllMappings(perPage = 100) {
        const allMappings = [];
        let page = 1;
        let hasNext = true;

        while (hasNext) {
            const data = await this.getMappings({ page, per_page: perPage });
            allMappings.push(...data.data);
            hasNext = data.pagination.has_next;
            page++;
        }

        return allMappings;
    }
}

// Example 1: Basic Data Access and DOM Manipulation
async function basicDataAccess() {
    console.log('=== Example 1: Basic Data Access ===');
    
    const client = new KEWPDatasetClient();
    
    try {
        // Get first page of mappings
        const data = await client.getMappings({ per_page: 20 });
        const mappings = data.data;
        const pagination = data.pagination;
        
        console.log(`Retrieved ${mappings.length} mappings (page 1 of ${pagination.pages})`);
        console.log(`Total mappings in dataset: ${pagination.total}`);
        
        // Display results in HTML if we're in a browser
        if (typeof document !== 'undefined') {
            displayMappingsInTable(mappings.slice(0, 5));
        }
        
        // Display first few mappings in console
        mappings.slice(0, 3).forEach((mapping, index) => {
            console.log(`\nMapping ${index + 1}:`);
            console.log(`  KE: ${mapping.ke_id} - ${mapping.ke_title}`);
            console.log(`  WP: ${mapping.wp_id} - ${mapping.wp_title}`);
            console.log(`  Confidence: ${mapping.confidence_level}`);
            console.log(`  Connection: ${mapping.connection_type}`);
        });
        
        return mappings;
    } catch (error) {
        console.error('Error in basic data access:', error);
    }
}

// Example 2: Advanced Filtering and Search
async function filteringAndSearch() {
    console.log('\n=== Example 2: Filtering and Search ===');
    
    const client = new KEWPDatasetClient();
    
    try {
        // Search for oxidative stress related mappings
        const oxidativeResults = await client.searchMappings('oxidative stress', { per_page: 10 });
        console.log(`Found ${oxidativeResults.data.length} mappings related to 'oxidative stress'`);
        
        // Filter by high confidence causative relationships
        const highConfResults = await client.getMappings({
            confidence_level: 'high',
            connection_type: 'causative',
            per_page: 20
        });
        console.log(`Found ${highConfResults.data.length} high-confidence causative mappings`);
        
        // Combined filter example
        const complexFilter = await client.getMappings({
            confidence_level: 'high',
            search: 'apoptosis',
            sort_by: 'created_at',
            sort_order: 'desc',
            per_page: 15
        });
        console.log(`Found ${complexFilter.data.length} high-confidence apoptosis mappings`);
        
        return { oxidativeResults, highConfResults, complexFilter };
    } catch (error) {
        console.error('Error in filtering and search:', error);
    }
}

// Example 3: Data Visualization with Chart.js (if available)
async function createVisualization() {
    console.log('\n=== Example 3: Data Visualization ===');
    
    const client = new KEWPDatasetClient();
    
    try {
        const stats = await client.getStatistics();
        const data = stats.data;
        
        // Create confidence level chart
        if (typeof Chart !== 'undefined' && document.getElementById('confidenceChart')) {
            const confidenceData = data.distributions.confidence_levels;
            
            new Chart(document.getElementById('confidenceChart'), {
                type: 'pie',
                data: {
                    labels: Object.keys(confidenceData),
                    datasets: [{
                        data: Object.values(confidenceData),
                        backgroundColor: ['#ff6b6b', '#4ecdc4', '#45b7d1'],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Confidence Level Distribution'
                        },
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
        
        // Create connection type chart
        if (typeof Chart !== 'undefined' && document.getElementById('connectionChart')) {
            const connectionData = data.distributions.connection_types;
            
            new Chart(document.getElementById('connectionChart'), {
                type: 'bar',
                data: {
                    labels: Object.keys(connectionData),
                    datasets: [{
                        label: 'Number of Mappings',
                        data: Object.values(connectionData),
                        backgroundColor: ['#ff9f43', '#10ac84', '#ee5a24', '#0abde3'],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Connection Type Distribution'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        console.log('Visualization created successfully');
        return data;
    } catch (error) {
        console.error('Error creating visualization:', error);
    }
}

// Example 4: Interactive Search Interface
function createSearchInterface() {
    console.log('\n=== Example 4: Interactive Search Interface ===');
    
    if (typeof document === 'undefined') {
        console.log('DOM not available, skipping interactive interface');
        return;
    }
    
    const client = new KEWPDatasetClient();
    let searchTimeout;
    
    // Create search interface HTML
    const searchContainer = document.getElementById('searchContainer');
    if (searchContainer) {
        searchContainer.innerHTML = `
            <div class="search-interface">
                <h3>Search KE-WP Mappings</h3>
                <div class="search-controls">
                    <input type="text" id="searchInput" placeholder="Search mappings..." class="search-input">
                    <select id="confidenceFilter" class="filter-select">
                        <option value="">All Confidence Levels</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                    <select id="connectionFilter" class="filter-select">
                        <option value="">All Connection Types</option>
                        <option value="causative">Causative</option>
                        <option value="responsive">Responsive</option>
                        <option value="other">Other</option>
                        <option value="undefined">Undefined</option>
                    </select>
                </div>
                <div id="searchResults" class="search-results"></div>
                <div id="loadingIndicator" class="loading" style="display: none;">Searching...</div>
            </div>
        `;
        
        // Add event listeners
        const searchInput = document.getElementById('searchInput');
        const confidenceFilter = document.getElementById('confidenceFilter');
        const connectionFilter = document.getElementById('connectionFilter');
        const searchResults = document.getElementById('searchResults');
        const loadingIndicator = document.getElementById('loadingIndicator');
        
        async function performSearch() {
            const query = searchInput.value.trim();
            const confidence = confidenceFilter.value;
            const connection = connectionFilter.value;
            
            if (!query && !confidence && !connection) {
                searchResults.innerHTML = '<p>Enter search terms or select filters</p>';
                return;
            }
            
            loadingIndicator.style.display = 'block';
            searchResults.innerHTML = '';
            
            try {
                const params = { per_page: 20 };
                if (query) params.search = query;
                if (confidence) params.confidence_level = confidence;
                if (connection) params.connection_type = connection;
                
                const results = await client.getMappings(params);
                displaySearchResults(results.data, searchResults);
                
            } catch (error) {
                searchResults.innerHTML = `<p class="error">Error: ${error.message}</p>`;
            } finally {
                loadingIndicator.style.display = 'none';
            }
        }
        
        // Debounced search
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(performSearch, 300);
        });
        
        confidenceFilter.addEventListener('change', performSearch);
        connectionFilter.addEventListener('change', performSearch);
    }
}

// Example 5: Data Export and Download
async function dataExportExample() {
    console.log('\n=== Example 5: Data Export and Download ===');
    
    const client = new KEWPDatasetClient();
    
    try {
        // Get available export formats
        const formatsResponse = await client.makeRequest('/export/formats');
        const formats = await formatsResponse.json();
        
        console.log('Available export formats:', formats.available_formats);
        
        // Export as JSON
        const jsonResponse = await client.exportData('json', { 
            metadata: 'true', 
            provenance: 'true' 
        });
        const jsonData = await jsonResponse.json();
        console.log(`JSON export contains ${jsonData.mappings.length} mappings`);
        
        // Create download link for JSON (browser only)
        if (typeof document !== 'undefined') {
            createDownloadLink(JSON.stringify(jsonData, null, 2), 'ke_wp_dataset.json', 'application/json');
        }
        
        // Export as CSV
        const csvResponse = await client.makeRequest('/download');
        const csvData = await csvResponse.text();
        console.log('CSV export completed');
        
        // Create download link for CSV (browser only)
        if (typeof document !== 'undefined') {
            createDownloadLink(csvData, 'ke_wp_dataset.csv', 'text/csv');
        }
        
        return { jsonData, csvData, formats };
    } catch (error) {
        console.error('Error in data export:', error);
    }
}

// Example 6: Real-time Statistics Dashboard
async function createStatsDashboard() {
    console.log('\n=== Example 6: Real-time Statistics Dashboard ===');
    
    if (typeof document === 'undefined') {
        console.log('DOM not available, skipping dashboard');
        return;
    }
    
    const client = new KEWPDatasetClient();
    const dashboardContainer = document.getElementById('statsContainer');
    
    if (!dashboardContainer) {
        console.log('Stats container not found');
        return;
    }
    
    async function updateDashboard() {
        try {
            const stats = await client.getStatistics();
            const data = stats.data;
            
            dashboardContainer.innerHTML = `
                <div class="stats-dashboard">
                    <h3>Dataset Statistics</h3>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <h4>Total Mappings</h4>
                            <div class="stat-value">${data.summary.total_mappings.toLocaleString()}</div>
                        </div>
                        <div class="stat-card">
                            <h4>Unique Key Events</h4>
                            <div class="stat-value">${data.summary.unique_key_events.toLocaleString()}</div>
                        </div>
                        <div class="stat-card">
                            <h4>Unique Pathways</h4>
                            <div class="stat-value">${data.summary.unique_pathways.toLocaleString()}</div>
                        </div>
                        <div class="stat-card">
                            <h4>Contributors</h4>
                            <div class="stat-value">${data.summary.contributors.toLocaleString()}</div>
                        </div>
                    </div>
                    <div class="distribution-stats">
                        <div class="distribution-item">
                            <h4>Confidence Levels</h4>
                            ${Object.entries(data.distributions.confidence_levels)
                                .map(([level, count]) => 
                                    `<div class="distribution-bar">
                                        <span class="label">${level}:</span>
                                        <div class="bar" style="width: ${count / data.summary.total_mappings * 100}%"></div>
                                        <span class="value">${count}</span>
                                    </div>`
                                ).join('')}
                        </div>
                        <div class="distribution-item">
                            <h4>Connection Types</h4>
                            ${Object.entries(data.distributions.connection_types)
                                .map(([type, count]) => 
                                    `<div class="distribution-bar">
                                        <span class="label">${type}:</span>
                                        <div class="bar" style="width: ${count / data.summary.total_mappings * 100}%"></div>
                                        <span class="value">${count}</span>
                                    </div>`
                                ).join('')}
                        </div>
                    </div>
                    <div class="last-updated">
                        Last updated: ${new Date(stats.meta.timestamp).toLocaleString()}
                    </div>
                </div>
            `;
            
        } catch (error) {
            dashboardContainer.innerHTML = `<p class="error">Error loading statistics: ${error.message}</p>`;
        }
    }
    
    // Initial load
    await updateDashboard();
    
    // Auto-refresh every 5 minutes
    setInterval(updateDashboard, 5 * 60 * 1000);
    
    return updateDashboard;
}

// Example 7: Integration with External APIs
async function externalAPIIntegration() {
    console.log('\n=== Example 7: External API Integration ===');
    
    const client = new KEWPDatasetClient();
    
    try {
        // Get some mappings for analysis
        const data = await client.getMappings({ per_page: 10, confidence_level: 'high' });
        const mappings = data.data;
        
        console.log('Analyzing pathway integration opportunities...');
        
        // Extract unique pathway IDs
        const pathwayIds = [...new Set(mappings.map(m => m.wp_id))];
        
        // Generate URLs for external services
        const externalUrls = pathwayIds.map(wpId => ({
            wp_id: wpId,
            wikipathways_url: `https://www.wikipathways.org/pathways/${wpId}.html`,
            svg_diagram: `https://www.wikipathways.org/wikipathways-assets/pathways/${wpId}/${wpId}.svg`,
            rdf_data: `https://rdf.wikipathways.org/WP${wpId.replace('WP', '')}`
        }));
        
        console.log('External integration URLs generated for', pathwayIds.length, 'pathways');
        
        // Example: Fetch pathway SVG (first one only to avoid overwhelming requests)
        if (externalUrls.length > 0) {
            try {
                const svgResponse = await fetch(externalUrls[0].svg_diagram);
                if (svgResponse.ok) {
                    const svgContent = await svgResponse.text();
                    console.log(`Successfully fetched SVG diagram for ${externalUrls[0].wp_id} (${svgContent.length} chars)`);
                    
                    // Display SVG in browser if available
                    if (typeof document !== 'undefined') {
                        const svgContainer = document.getElementById('svgContainer');
                        if (svgContainer) {
                            svgContainer.innerHTML = `
                                <h4>Pathway Diagram: ${externalUrls[0].wp_id}</h4>
                                ${svgContent}
                            `;
                        }
                    }
                }
            } catch (svgError) {
                console.log('Could not fetch SVG diagram:', svgError.message);
            }
        }
        
        return { mappings, externalUrls };
    } catch (error) {
        console.error('Error in external API integration:', error);
    }
}

// Utility Functions

function displayMappingsInTable(mappings) {
    const tableContainer = document.getElementById('mappingsTable');
    if (!tableContainer) return;
    
    const tableHTML = `
        <table class="mappings-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Key Event</th>
                    <th>Pathway</th>
                    <th>Confidence</th>
                    <th>Connection</th>
                    <th>Created By</th>
                </tr>
            </thead>
            <tbody>
                ${mappings.map(mapping => `
                    <tr>
                        <td>${mapping.id}</td>
                        <td title="${mapping.ke_title}">${mapping.ke_id}<br><small>${mapping.ke_title.substring(0, 50)}...</small></td>
                        <td title="${mapping.wp_title}">${mapping.wp_id}<br><small>${mapping.wp_title.substring(0, 50)}...</small></td>
                        <td><span class="confidence-badge confidence-${mapping.confidence_level}">${mapping.confidence_level}</span></td>
                        <td><span class="connection-badge connection-${mapping.connection_type}">${mapping.connection_type}</span></td>
                        <td>${mapping.created_by || 'N/A'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    
    tableContainer.innerHTML = tableHTML;
}

function displaySearchResults(mappings, container) {
    if (mappings.length === 0) {
        container.innerHTML = '<p>No mappings found matching your criteria</p>';
        return;
    }
    
    const resultsHTML = `
        <div class="search-results-header">
            <h4>Found ${mappings.length} mappings</h4>
        </div>
        <div class="results-list">
            ${mappings.map(mapping => `
                <div class="result-item">
                    <div class="result-main">
                        <h5>${mapping.ke_id}: ${mapping.ke_title}</h5>
                        <p><strong>Pathway:</strong> ${mapping.wp_id}: ${mapping.wp_title}</p>
                    </div>
                    <div class="result-meta">
                        <span class="confidence-badge confidence-${mapping.confidence_level}">${mapping.confidence_level}</span>
                        <span class="connection-badge connection-${mapping.connection_type}">${mapping.connection_type}</span>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    container.innerHTML = resultsHTML;
}

function createDownloadLink(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    
    const downloadContainer = document.getElementById('downloadContainer') || document.body;
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.textContent = `Download ${filename}`;
    link.className = 'download-link';
    
    downloadContainer.appendChild(link);
    
    // Clean up URL after a delay
    setTimeout(() => URL.revokeObjectURL(url), 5000);
}

// Main execution function
async function runAllExamples() {
    console.log('KE-WP Mapping Dataset - JavaScript Examples');
    console.log('='.repeat(50));
    
    try {
        await basicDataAccess();
        await filteringAndSearch();
        await createVisualization();
        createSearchInterface();
        await dataExportExample();
        await createStatsDashboard();
        await externalAPIIntegration();
        
        console.log('\n' + '='.repeat(50));
        console.log('All examples completed successfully!');
        
        if (typeof document !== 'undefined') {
            console.log('Check the generated HTML elements and download links in the page');
        }
        
    } catch (error) {
        console.error('Error running examples:', error);
    }
}

// CSS Styles (to be included in HTML)
const cssStyles = `
<style>
.search-interface {
    max-width: 800px;
    margin: 20px 0;
    padding: 20px;
    border: 1px solid #ddd;
    border-radius: 8px;
}

.search-controls {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.search-input, .filter-select {
    padding: 8px 12px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 14px;
}

.search-input {
    flex: 1;
    min-width: 200px;
}

.result-item {
    padding: 15px;
    border: 1px solid #eee;
    border-radius: 6px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
}

.result-main h5 {
    margin: 0 0 8px 0;
    color: #333;
}

.result-main p {
    margin: 0;
    color: #666;
}

.result-meta {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.confidence-badge, .connection-badge {
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
    text-align: center;
    min-width: 60px;
}

.confidence-high { background: #d4edda; color: #155724; }
.confidence-medium { background: #fff3cd; color: #856404; }
.confidence-low { background: #f8d7da; color: #721c24; }

.connection-causative { background: #cce5ff; color: #004085; }
.connection-responsive { background: #d1ecf1; color: #0c5460; }
.connection-other { background: #e2e3e5; color: #383d41; }
.connection-undefined { background: #f5f5f5; color: #6c757d; }

.stats-dashboard {
    max-width: 900px;
    margin: 20px 0;
    padding: 20px;
    border: 1px solid #ddd;
    border-radius: 8px;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-bottom: 30px;
}

.stat-card {
    text-align: center;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 6px;
}

.stat-card h4 {
    margin: 0 0 10px 0;
    color: #495057;
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.stat-value {
    font-size: 28px;
    font-weight: bold;
    color: #307BBF;
}

.distribution-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
}

.distribution-item h4 {
    margin: 0 0 15px 0;
    color: #495057;
}

.distribution-bar {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    gap: 10px;
}

.distribution-bar .label {
    min-width: 80px;
    font-size: 12px;
    color: #6c757d;
}

.distribution-bar .bar {
    height: 20px;
    background: #307BBF;
    border-radius: 10px;
    min-width: 3px;
    flex-grow: 1;
    max-width: 200px;
}

.distribution-bar .value {
    min-width: 40px;
    text-align: right;
    font-size: 12px;
    font-weight: bold;
    color: #495057;
}

.mappings-table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
}

.mappings-table th,
.mappings-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

.mappings-table th {
    background-color: #f8f9fa;
    font-weight: bold;
}

.mappings-table tbody tr:hover {
    background-color: #f8f9fa;
}

.download-link {
    display: inline-block;
    margin: 10px;
    padding: 10px 20px;
    background: #307BBF;
    color: white;
    text-decoration: none;
    border-radius: 5px;
    font-weight: bold;
}

.download-link:hover {
    background: #2c5282;
}

.loading {
    text-align: center;
    padding: 20px;
    color: #6c757d;
    font-style: italic;
}

.error {
    color: #dc3545;
    background: #f8d7da;
    padding: 10px;
    border-radius: 4px;
    border: 1px solid #f5c6cb;
}

.last-updated {
    text-align: center;
    margin-top: 20px;
    color: #6c757d;
    font-size: 12px;
}

@media (max-width: 768px) {
    .search-controls {
        flex-direction: column;
    }
    
    .stats-grid {
        grid-template-columns: 1fr;
    }
    
    .distribution-stats {
        grid-template-columns: 1fr;
    }
    
    .result-item {
        flex-direction: column;
        gap: 10px;
    }
}
</style>
`;

// Export for use in Node.js or browser
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        KEWPDatasetClient,
        runAllExamples,
        basicDataAccess,
        filteringAndSearch,
        createVisualization,
        createSearchInterface,
        dataExportExample,
        createStatsDashboard,
        externalAPIIntegration,
        cssStyles
    };
}

// Auto-run in browser if DOM is loaded
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', runAllExamples);
    } else {
        runAllExamples();
    }
}