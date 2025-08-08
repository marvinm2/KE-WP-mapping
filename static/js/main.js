/**
 * Main JavaScript functionality for KE-WP Mapping Application
 */

class KEWPApp {
    constructor() {
        this.isLoggedIn = false;
        this.csrfToken = null;
        this.stepAnswers = {};
        this.init();
    }

    init() {
        this.setupCSRF();
        this.setupEventListeners();
        this.loadDropdownOptions();
        
        // Debug: Check if form exists
        console.log("Form element found:", $("#mapping-form").length > 0);
        console.log("Submit button found:", $("#mapping-form button[type='submit']").length > 0);
    }

    setupCSRF() {
        // Get CSRF token from meta tag or input field
        this.csrfToken = $('meta[name="csrf-token"]').attr('content') || $('input[name="csrf_token"]').val();
        
        if (!this.csrfToken) {
            console.warn('CSRF token not found');
            return;
        }
        
        // Setup CSRF token for all AJAX requests
        $.ajaxSetup({
            beforeSend: (xhr, settings) => {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRFToken", this.csrfToken);
                }
            }
        });
        
        console.log('CSRF token configured for AJAX requests');
    }

    setupEventListeners() {
        // Retrieve login status
        this.isLoggedIn = $("body").data("is-logged-in") === true;
        console.log("User login status:", this.isLoggedIn);

        // Form submission handler
        $("#mapping-form").on('submit', (e) => {
            console.log("Form submit event triggered!");
            this.handleFormSubmission(e);
        });

        // Confidence assessment handlers
        $(".btn-group").on("click", ".btn-option", (e) => this.handleConfidenceAssessment(e));

        // Dropdown change handlers
        $("#ke_id, #wp_id").on('change', () => this.toggleAssessmentSection());
        
        // KE selection change handler for preview
        $("#ke_id").on('change', (e) => this.handleKESelection(e));
        
        // Pathway selection change handler for preview
        $("#wp_id").on('change', (e) => this.handlePathwaySelection(e));
        
        // Debug: Direct button click handler
        $("#mapping-form button[type='submit']").on('click', (e) => {
            console.log("Submit button clicked directly!");
            e.preventDefault();
            // Trigger the form submission manually
            $("#mapping-form").trigger('submit');
        });
    }

    loadDropdownOptions() {
        this.loadKEOptions();
        this.loadPathwayOptions();
    }

    loadKEOptions() {
        $.getJSON("/get_ke_options")
            .done((data) => {
                console.log(`Loaded ${data.length} KE options`);
                
                // Sort data by KE Label numerically
                data.sort((a, b) => {
                    const matchA = a.KElabel.match(/\d+/);
                    const matchB = b.KElabel.match(/\d+/);
                    const idA = matchA ? parseInt(matchA[0]) : 0;
                    const idB = matchB ? parseInt(matchB[0]) : 0;
                    return idA - idB;
                });

                // Populate KE ID dropdown
                const dropdown = $("#ke_id");
                dropdown.empty();
                dropdown.append('<option value="" disabled selected>Select a Key Event</option>');
                data.forEach(option => {
                    dropdown.append(
                        `<option value="${option.KElabel}" 
                         data-title="${option.KEtitle}"
                         data-description="${option.KEdescription || ''}"
                         data-biolevel="${option.biolevel || ''}">${option.KElabel} - ${option.KEtitle}</option>`
                    );
                });
            })
            .fail((xhr, status, error) => {
                console.error("Failed to load KE options:", error);
                const errorMsg = xhr.responseJSON?.error || "Failed to load Key Events";
                this.showMessage(errorMsg, "error");
            });
    }

    loadPathwayOptions() {
        $.getJSON("/get_pathway_options")
            .done((data) => {
                console.log(`Loaded ${data.length} pathway options`);
                
                // Sort data by Pathway ID numerically
                data.sort((a, b) => {
                    const matchA = a.pathwayID.match(/\d+/);
                    const matchB = b.pathwayID.match(/\d+/);
                    const idA = matchA ? parseInt(matchA[0]) : 0;
                    const idB = matchB ? parseInt(matchB[0]) : 0;
                    return idA - idB;
                });

                // Populate Pathway ID dropdown
                const dropdown = $("#wp_id");
                dropdown.empty();
                dropdown.append('<option value="" disabled selected>Select a Pathway</option>');
                data.forEach(option => {
                    dropdown.append(
                        `<option value="${option.pathwayID}" 
                         data-title="${option.pathwayTitle}"
                         data-description="${option.pathwayDescription || ''}">${option.pathwayID} - ${option.pathwayTitle}</option>`
                    );
                });
            })
            .fail((xhr, status, error) => {
                console.error("Failed to load Pathway options:", error);
                const errorMsg = xhr.responseJSON?.error || "Failed to load Pathways";
                this.showMessage(errorMsg, "error");
            });
    }

    handleFormSubmission(event) {
        event.preventDefault();
        console.log("Form submission started");

        const formData = {
            ke_id: $("#ke_id").val(),
            ke_title: $("#ke_id option:selected").data("title"),
            wp_id: $("#wp_id").val(),
            wp_title: $("#wp_id option:selected").data("title"),
            connection_type: $("#connection_type").val(),
            confidence_level: $("#confidence_level").val(),
            csrf_token: this.csrfToken
        };

        console.log("Form data:", formData);

        // Validate required fields
        if (!formData.ke_id || !formData.wp_id) {
            this.showMessage("Please select both a Key Event and a Pathway", "error");
            return;
        }

        if (!formData.connection_type || !formData.confidence_level) {
            this.showMessage("Please complete the confidence assessment", "error");
            console.log("Missing confidence/connection data:", {
                connection_type: formData.connection_type,
                confidence_level: formData.confidence_level
            });
            return;
        }

        // First, check for duplicates
        this.checkEntry(formData);
    }

    checkEntry(formData) {
        $.post("/check", formData)
            .done((response) => {
                $("#existing-entries").html(""); // Clear previous content
                if (response.pair_exists) {
                    this.showMessage(response.message, "error");
                } else if (response.ke_exists) {
                    this.showExistingEntries(response, formData);
                } else {
                    this.showMappingPreview(formData);
                }
            })
            .fail((xhr) => {
                const errorMsg = xhr.responseJSON?.error || "Failed to check entry";
                this.showMessage(errorMsg, "error");
            });
    }

    showExistingEntries(response, formData) {
        let tableHTML = `
            <div class="existing-entries-container">
                <p>${response.message}</p>
                <table class="existing-entries-table">
                    <thead>
                        <tr>
                            <th>KE ID</th>
                            <th>WP ID</th>
                            <th>Connection Type</th>
                            <th>Confidence Level</th>
                            <th>Created At</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        response.ke_matches.forEach(entry => {
            tableHTML += `
                <tr>
                    <td>${entry.ke_id || entry.KE_ID}</td>
                    <td>${entry.wp_id || entry.WP_ID}</td>
                    <td>${entry.connection_type || entry.Connection_Type}</td>
                    <td>${entry.confidence_level || entry.Confidence_Level}</td>
                    <td>${(entry.created_at || entry.Timestamp || '').split('.')[0]}</td>
                </tr>
            `;
        });
        
        tableHTML += `
                    </tbody>
                </table>
                <hr style="margin: 20px 0;">
            </div>
        `;
        
        $("#existing-entries").html(tableHTML);
        
        // Also show the mapping preview for the new entry
        this.showMappingPreviewAfterTable(formData);
    }

    showMappingPreviewAfterTable(formData) {
        // This is similar to showMappingPreview but appends to existing content
        const selectedKE = $("#ke_id option:selected");
        const selectedPW = $("#wp_id option:selected");
        const keDescription = selectedKE.data('description') || '';
        const pwDescription = selectedPW.data('description') || '';
        const biolevel = selectedKE.data('biolevel') || '';
        
        // Get user information from body attributes or session
        const isLoggedIn = $("body").data("is-logged-in") === true;
        let userInfo = 'Anonymous';
        if (isLoggedIn) {
            // Try to get username from the welcome message in the header
            const welcomeText = $('header nav p').text();
            const usernameMatch = welcomeText.match(/Welcome,\s*([^(]+)/);
            if (usernameMatch) {
                userInfo = `GitHub: ${usernameMatch[1].trim()}`;
            } else {
                userInfo = 'GitHub user (logged in)';
            }
        }
        const currentDate = new Date().toLocaleString();
        
        // Create collapsible descriptions
        const keDescHtml = this.createCollapsibleDescription(keDescription, 'preview-ke-desc-table');
        const pwDescHtml = this.createCollapsibleDescription(pwDescription, 'preview-pw-desc-table');
        
        let previewHTML = `
                <h3>🔍 New Mapping Preview</h3>
                <p>Review your new mapping that will be added:</p>
                
                <div class="mapping-preview" style="display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 20px; margin: 20px 0; width: 100%;">
                    <div class="preview-section ke-section" style="background-color: #f0f8ff; padding: 15px; border-radius: 8px; border-left: 4px solid #307BBF; min-width: 0; word-wrap: break-word;">
                        <h4 style="color: #307BBF; margin-top: 0;">🧬 Key Event Information</h4>
                        <p><strong>KE ID:</strong> ${formData.ke_id}</p>
                        <p><strong>KE Title:</strong> ${formData.ke_title}</p>
                        <p><strong>Biological Level:</strong> <span style="background-color: #e3f2fd; padding: 2px 6px; border-radius: 3px;">${biolevel || 'Not specified'}</span></p>
                        <div><strong>Description:</strong><br/>${keDescHtml}</div>
                    </div>
                    
                    <div class="preview-section wp-section" style="background-color: #f0fff0; padding: 15px; border-radius: 8px; border-left: 4px solid #E6007E; min-width: 0; word-wrap: break-word;">
                        <h4 style="color: #E6007E; margin-top: 0;">🛤️ Pathway Information</h4>
                        <p><strong>WP ID:</strong> ${formData.wp_id}</p>
                        <p><strong>WP Title:</strong> ${formData.wp_title}</p>
                        <div><strong>Description:</strong><br/>${pwDescHtml}</div>
                    </div>
                </div>
                
                <div class="preview-section" style="background-color: #fff8f0; padding: 15px; border-radius: 8px; border-left: 4px solid #EB5B25; margin: 20px 0;">
                    <h4 style="color: #EB5B25; margin-top: 0;">📊 Mapping Metadata</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div>
                            <p><strong>Connection Type:</strong> <span style="background-color: #ffd7b5; padding: 2px 8px; border-radius: 3px; font-weight: 600;">${formData.connection_type.charAt(0).toUpperCase() + formData.connection_type.slice(1)}</span></p>
                            <p><strong>Confidence Level:</strong> <span style="background-color: #ffd7b5; padding: 2px 8px; border-radius: 3px; font-weight: 600;">${formData.confidence_level.charAt(0).toUpperCase() + formData.confidence_level.slice(1)}</span></p>
                        </div>
                        <div>
                            <p><strong>Submitted by:</strong> ${userInfo}</p>
                            <p><strong>Submission time:</strong> ${currentDate}</p>
                            <p><strong>Entry status:</strong> <span style="color: #28a745; font-weight: 600;">New mapping</span></p>
                            <p><strong>Data sources:</strong> <span style="font-size: 12px; color: #666;">AOP-Wiki, WikiPathways</span></p>
                        </div>
                    </div>
                </div>
                
                <div class="confirmation-section" style="text-align: center; margin: 25px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
                    <p style="font-size: 16px; margin-bottom: 15px;"><strong>⚠️ Do you want to add this new KE-WP mapping?</strong></p>
                    <p style="color: #666; margin-bottom: 20px; font-size: 14px;">This will be added alongside the existing mappings shown above.</p>
                    <button id="confirm-submit" class="btn btn-success" style="background-color: #28a745; margin-right: 10px; padding: 10px 20px;">✅ Yes, Add Entry</button>
                    <button id="cancel-submit" class="btn btn-secondary" style="background-color: #6c757d; padding: 10px 20px;">❌ Cancel</button>
                </div>
        `;
        
        // Append to existing content
        $("#existing-entries").append(previewHTML);
        
        // Handle confirmation buttons
        $("#confirm-submit").on('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            this.submitEntry(formData);
        });

        $("#cancel-submit").on('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            $("#existing-entries").html("");
        });
    }

    showMappingPreview(formData) {
        // Get additional data from selected options
        const selectedKE = $("#ke_id option:selected");
        const selectedPW = $("#wp_id option:selected");
        const keDescription = selectedKE.data('description') || '';
        const pwDescription = selectedPW.data('description') || '';
        const biolevel = selectedKE.data('biolevel') || '';
        
        // Get user information from body attributes or session
        const isLoggedIn = $("body").data("is-logged-in") === true;
        let userInfo = 'Anonymous';
        if (isLoggedIn) {
            // Try to get username from the welcome message in the header
            const welcomeText = $('header nav p').text();
            const usernameMatch = welcomeText.match(/Welcome,\s*([^(]+)/);
            if (usernameMatch) {
                userInfo = `GitHub: ${usernameMatch[1].trim()}`;
            } else {
                userInfo = 'GitHub user (logged in)';
            }
        }
        const currentDate = new Date().toLocaleString();
        
        // Create collapsible descriptions
        const keDescHtml = this.createCollapsibleDescription(keDescription, 'preview-ke-desc');
        const pwDescHtml = this.createCollapsibleDescription(pwDescription, 'preview-pw-desc');
        
        let previewHTML = `
            <div class="existing-entries-container">
                <h3>🔍 Mapping Preview & Confirmation</h3>
                <p>Please carefully review your mapping details before submitting:</p>
                
                <div class="mapping-preview" style="display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 20px; margin: 20px 0; width: 100%;">
                    <div class="preview-section ke-section" style="background-color: #f0f8ff; padding: 15px; border-radius: 8px; border-left: 4px solid #307BBF; min-width: 0; word-wrap: break-word;">
                        <h4 style="color: #307BBF; margin-top: 0;">🧬 Key Event Information</h4>
                        <p><strong>KE ID:</strong> ${formData.ke_id}</p>
                        <p><strong>KE Title:</strong> ${formData.ke_title}</p>
                        <p><strong>Biological Level:</strong> <span style="background-color: #e3f2fd; padding: 2px 6px; border-radius: 3px;">${biolevel || 'Not specified'}</span></p>
                        <div><strong>Description:</strong><br/>${keDescHtml}</div>
                    </div>
                    
                    <div class="preview-section wp-section" style="background-color: #f0fff0; padding: 15px; border-radius: 8px; border-left: 4px solid #E6007E; min-width: 0; word-wrap: break-word;">
                        <h4 style="color: #E6007E; margin-top: 0;">🛤️ Pathway Information</h4>
                        <p><strong>WP ID:</strong> ${formData.wp_id}</p>
                        <p><strong>WP Title:</strong> ${formData.wp_title}</p>
                        <div><strong>Description:</strong><br/>${pwDescHtml}</div>
                    </div>
                </div>
                
                <div class="preview-section" style="background-color: #fff8f0; padding: 15px; border-radius: 8px; border-left: 4px solid #EB5B25; margin: 20px 0;">
                    <h4 style="color: #EB5B25; margin-top: 0;">📊 Mapping Metadata</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div>
                            <p><strong>Connection Type:</strong> <span style="background-color: #ffd7b5; padding: 2px 8px; border-radius: 3px; font-weight: 600;">${formData.connection_type.charAt(0).toUpperCase() + formData.connection_type.slice(1)}</span></p>
                            <p><strong>Confidence Level:</strong> <span style="background-color: #ffd7b5; padding: 2px 8px; border-radius: 3px; font-weight: 600;">${formData.confidence_level.charAt(0).toUpperCase() + formData.confidence_level.slice(1)}</span></p>
                        </div>
                        <div>
                            <p><strong>Submitted by:</strong> ${userInfo}</p>
                            <p><strong>Submission time:</strong> ${currentDate}</p>
                            <p><strong>Entry status:</strong> <span style="color: #28a745; font-weight: 600;">New mapping</span></p>
                            <p><strong>Data sources:</strong> <span style="font-size: 12px; color: #666;">AOP-Wiki, WikiPathways</span></p>
                        </div>
                    </div>
                </div>
                
                <div class="confirmation-section" style="text-align: center; margin: 25px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
                    <p style="font-size: 16px; margin-bottom: 15px;"><strong>⚠️ Are you sure you want to submit this mapping?</strong></p>
                    <p style="color: #666; margin-bottom: 20px; font-size: 14px;">This action will add the mapping to the database and make it available for other researchers.</p>
                    <button id="confirm-final-submit" class="btn btn-success" style="background-color: #28a745; margin-right: 10px; padding: 10px 20px;">✅ Yes, Submit Mapping</button>
                    <button id="cancel-final-submit" class="btn btn-secondary" style="background-color: #6c757d; padding: 10px 20px;">❌ Cancel</button>
                </div>
            </div>
        `;
        
        $("#existing-entries").html(previewHTML);

        // Handle confirmation buttons
        $("#confirm-final-submit").on('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            this.submitEntry(formData);
        });

        $("#cancel-final-submit").on('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            $("#existing-entries").html("");
        });
    }

    submitEntry(formData) {
        // Show loading state
        this.showMessage("Submitting your mapping...", "info");
        
        $.post("/submit", formData)
            .done((response) => {
                // Show success message with visual feedback
                this.showSuccessMessage(response.message, formData);
                $("#existing-entries").html("");
                this.resetForm();
            })
            .fail((xhr) => {
                const errorMsg = xhr.responseJSON?.error || "Failed to submit entry";
                this.showMessage(errorMsg, "error");
            });
    }

    handleConfidenceAssessment(event) {
        const $btn = $(event.target);
        const $group = $btn.closest(".btn-group");
        const stepId = $group.data("step");
        const selectedValue = $btn.data("value");

        // Save the value
        this.stepAnswers[stepId] = selectedValue;

        // Update UI
        $group.find(".btn-option").removeClass("selected");
        $btn.addClass("selected");

        // Show/hide next steps based on logic
        this.handleStepProgression();
    }

    handleStepProgression() {
        const s1 = this.stepAnswers["step1"];
        const s2 = this.stepAnswers["step2"];
        const s2b = this.stepAnswers["step2b"];
        const s3 = this.stepAnswers["step3"];
        const s4 = this.stepAnswers["step4"];
        const s5 = this.stepAnswers["step5"];
        const s6 = this.stepAnswers["step6"];

        // Reset visibility
        $("#step2, #step2b, #step3, #step4, #step5, #step6").hide();
        $("#evaluateBtn").hide();

        if (s1 === "yes") {
            $("#step2").show();
        } else if (s1 === "no") {
            $("#ca-result").text("Assessment stopped: Pathway is not biologically related to the Key Event.");
            return;
        }

        if (s2) {
            $("#step2b").show();
            $("#step3").show();
        }

        if (s3) {
            $("#step4").show();
        }
        if (s4) {
            $("#step5").show();
        }
        if (s5 === "medium") {
            $("#step6").show();
        }

        const ready = s1 && s2 && s2b && s3 && s4 && s5 && (s5 !== "medium" || s6);
        if (ready) {
            $("#evaluateBtn").show();
        }
    }

    handleKESelection(event) {
        const selectedOption = $(event.target).find('option:selected');
        const title = selectedOption.data('title') || '';
        const description = selectedOption.data('description') || '';
        const biolevel = selectedOption.data('biolevel') || '';
        
        // Show/hide KE preview
        if (title && description) {
            this.showKEPreview(title, description);
        } else {
            this.hideKEPreview();
        }
        
        // Store biological level for later use in assessment
        this.selectedBiolevel = biolevel;
        
        console.log('Selected KE:', { title, description, biolevel });
    }

    showKEPreview(title, description) {
        // Remove existing preview
        $("#ke-preview").remove();
        
        // Create collapsible description HTML
        const descriptionHTML = this.createCollapsibleDescription(description, 'ke-description');
        
        // Create preview HTML
        const previewHTML = `
            <div id="ke-preview" style="margin-top: 10px; padding: 15px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;">
                <h4 style="margin: 0 0 8px 0; color: #29235C;">Key Event Details:</h4>
                <p style="margin: 0 0 8px 0;"><strong>Title:</strong> ${title}</p>
                ${description ? `<div><strong>Description:</strong><br/>${descriptionHTML}</div>` : '<p style="margin: 0; color: #666; font-style: italic;">No description available</p>'}
            </div>
        `;
        
        // Insert after KE dropdown
        $("#ke_id").parent().after(previewHTML);
    }
    
    handlePathwaySelection(event) {
        const selectedOption = $(event.target).find('option:selected');
        const title = selectedOption.data('title') || '';
        const description = selectedOption.data('description') || '';
        
        // Show/hide pathway preview
        if (title) {
            this.showPathwayPreview(title, description);
        } else {
            this.hidePathwayPreview();
        }
        
        console.log('Selected Pathway:', { title, description });
    }

    showPathwayPreview(title, description) {
        // Remove existing preview
        $("#pathway-preview").remove();
        
        // Create collapsible description HTML
        const descriptionHTML = this.createCollapsibleDescription(description, 'pathway-description');
        
        // Create preview HTML
        const previewHTML = `
            <div id="pathway-preview" style="margin-top: 10px; padding: 15px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;">
                <h4 style="margin: 0 0 8px 0; color: #29235C;">Pathway Details:</h4>
                <p style="margin: 0 0 8px 0;"><strong>Title:</strong> ${title}</p>
                ${description ? `<div><strong>Description:</strong><br/>${descriptionHTML}</div>` : '<p style="margin: 0; color: #666; font-style: italic;">No description available</p>'}
            </div>
        `;
        
        // Insert after pathway dropdown
        $("#wp_id").parent().after(previewHTML);
    }

    hidePathwayPreview() {
        $("#pathway-preview").remove();
    }

    createCollapsibleDescription(description, id) {
        if (!description) return '<span style="color: #666; font-style: italic;">No description available</span>';
        
        const maxLength = 300;
        const isLong = description.length > maxLength;
        
        if (!isLong) {
            return `<div style="max-width: 100%; word-wrap: break-word; line-height: 1.4;">${description}</div>`;
        }
        
        const shortText = description.substring(0, maxLength) + '...';
        
        return `
            <div id="${id}" style="max-width: 100%; word-wrap: break-word; line-height: 1.4;">
                <div class="description-short">
                    ${shortText}
                    <br/><a href="#" onclick="KEWPApp.toggleDescription('${id}'); return false;" style="color: #307BBF; font-weight: bold;">Show full description</a>
                </div>
                <div class="description-full" style="display: none;">
                    ${description}
                    <br/><a href="#" onclick="KEWPApp.toggleDescription('${id}'); return false;" style="color: #307BBF; font-weight: bold;">Show less</a>
                </div>
            </div>
        `;
    }

    static toggleDescription(id) {
        const container = $(`#${id}`);
        const shortDiv = container.find('.description-short');
        const fullDiv = container.find('.description-full');
        
        if (shortDiv.is(':visible')) {
            shortDiv.hide();
            fullDiv.show();
        } else {
            shortDiv.show();
            fullDiv.hide();
        }
    }

    hideKEPreview() {
        $("#ke-preview").remove();
        this.selectedBiolevel = '';
    }

    toggleAssessmentSection() {
        const keSelected = $("#ke_id").val();
        const wpSelected = $("#wp_id").val();
        if (keSelected && wpSelected) {
            $("#confidence-guide").show();
            $("#confidence-guide")[0].scrollIntoView({ behavior: 'smooth' });
            // Pre-fill biological level if available
            this.preFillBiologicalLevel();
        } else {
            $("#confidence-guide").hide();
            this.resetGuide();
        }
    }

    resetGuide() {
        const sections = ["#step2", "#step3", "#step4", "#step5", "#step6", "#step2b"];
        sections.forEach(id => {
            $(id).hide().find("select").val("");
            $(id).find(".btn-option").removeClass("selected");
        });
        $("#evaluateBtn").hide();
        $("#ca-result").text("");
        $("#auto-confidence").text("—");
        $("#auto-connection").text("—");
        $("#confidence_level").val("");
        $("#connection_type").val("");
        this.stepAnswers = {};
    }

    preFillBiologicalLevel() {
        // Auto-select biological level based on KE data
        if (this.selectedBiolevel) {
            const levelMapping = {
                'molecular': 'yes',
                'cellular': 'yes', 
                'tissue': 'yes',
                'organ': 'no',
                'individual': 'no',
                'population': 'no'
            };
            
            const bioLevel = this.selectedBiolevel.toLowerCase();
            for (const [level, value] of Object.entries(levelMapping)) {
                if (bioLevel.includes(level)) {
                    this.stepAnswers["step2"] = value;
                    $("#step2 .btn-group").find(`.btn-option[data-value="${value}"]`).addClass('selected');
                    // Trigger step progression to show subsequent steps
                    this.handleStepProgression();
                    break;
                }
            }
        }
    }

    resetForm() {
        $("#ke_id, #wp_id").val("").trigger('change');
        this.hideKEPreview();
        this.hidePathwayPreview();
        this.resetGuide();
        $("#message").text("");
        this.selectedBiolevel = '';
    }

    showMessage(message, type = "info") {
        const color = type === "error" ? "red" : type === "success" ? "green" : "blue";
        $("#message").text(message).css("color", color).show();
        
        // Auto-hide success messages after 5 seconds
        if (type === "success") {
            setTimeout(() => {
                $("#message").fadeOut();
            }, 5000);
        }
    }

    showSuccessMessage(message, formData) {
        // Create a comprehensive success message with the submitted data
        const successHtml = `
            <div class="success-message" style="display: block;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <span class="success-icon">✅</span>
                    <strong>Mapping Successfully Submitted!</strong>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div style="background-color: #e3f2fd; padding: 10px; border-radius: 4px;">
                            <strong>🧬 Key Event:</strong><br>
                            <span style="font-family: monospace;">${formData.ke_id}</span><br>
                            <small style="color: #666;">${formData.ke_title}</small>
                        </div>
                        <div style="background-color: #e8f5e8; padding: 10px; border-radius: 4px;">
                            <strong>🛤️ Pathway:</strong><br>
                            <span style="font-family: monospace;">${formData.wp_id}</span><br>
                            <small style="color: #666;">${formData.wp_title}</small>
                        </div>
                    </div>
                    
                    <div style="text-align: center; margin-top: 15px; padding-top: 10px; border-top: 1px solid #ddd;">
                        <span style="background-color: #fff3cd; padding: 4px 8px; border-radius: 3px; margin: 0 5px;">
                            <strong>Connection:</strong> ${formData.connection_type.charAt(0).toUpperCase() + formData.connection_type.slice(1)}
                        </span>
                        <span style="background-color: #d1ecf1; padding: 4px 8px; border-radius: 3px; margin: 0 5px;">
                            <strong>Confidence:</strong> ${formData.confidence_level.charAt(0).toUpperCase() + formData.confidence_level.slice(1)}
                        </span>
                    </div>
                    
                    <p style="text-align: center; margin: 15px 0 5px 0; color: #28a745; font-weight: bold;">
                        🎉 Your mapping is now part of the research database!
                    </p>
                    <p style="text-align: center; font-size: 14px; color: #666; margin: 5px 0;">
                        View it in the <a href="/explore" target="_blank">dataset explorer</a> or submit another mapping below.
                    </p>
                </div>
            </div>
        `;
        
        // Show the success message in the existing entries area
        $("#existing-entries").html(successHtml);
        
        // Also show a simple message in the message area
        this.showMessage("✅ " + message, "success");
        
        // Auto-hide the detailed success message after 10 seconds
        setTimeout(() => {
            $("#existing-entries").fadeOut(1000, () => {
                $("#existing-entries").html("");
                $("#existing-entries").show();
            });
        }, 10000);
    }
}

// Global function for confidence evaluation
function evaluateConfidence() {
    const app = window.KEWPApp;
    const s1 = app.stepAnswers["step1"];
    const s2 = app.stepAnswers["step2"];
    const s2b = app.stepAnswers["step2b"];
    const s3 = app.stepAnswers["step3"];
    const s4 = app.stepAnswers["step4"];
    const s5 = app.stepAnswers["step5"];
    const s6 = app.stepAnswers["step6"];

    let confidence = "low";

    if (s3 === "no" || s5 === "low") {
        confidence = "low";
    } else if (s5 === "medium") {
        confidence = (s6 === "yes") ? "medium" : "low";
    } else if (s4 === "no") {
        confidence = "medium";
    } else {
        confidence = "high";
    }

    $("#auto-confidence").text(confidence.charAt(0).toUpperCase() + confidence.slice(1));
    $("#auto-connection").text(s2b.charAt(0).toUpperCase() + s2b.slice(1));
    $("#confidence_level").val(confidence);
    $("#connection_type").val(s2b);
    $("#evaluateBtn").hide();
    
    app.showMessage("Confidence assessment completed successfully", "success");
}

// Initialize app when document is ready
$(document).ready(() => {
    window.KEWPApp = new KEWPApp();
});