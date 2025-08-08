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
        
        // Pathway search functionality
        this.setupPathwaySearch();
        
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
        const keId = selectedOption.val();
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
        
        // Load pathway suggestions if KE is selected
        if (keId && title) {
            this.loadPathwaySuggestions(keId, title);
        } else {
            this.hidePathwaySuggestions();
        }
        
        console.log('Selected KE:', { keId, title, description, biolevel });
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

    loadPathwaySuggestions(keId, keTitle) {
        console.log(`Loading pathway suggestions for KE: ${keId} (bio_level: ${this.selectedBiolevel})`);
        
        // Show loading indicator
        this.showPathwaySuggestionsLoading();
        
        // Encode parameters for URL
        const encodedKeId = encodeURIComponent(keId);
        const encodedKeTitle = encodeURIComponent(keTitle);
        const encodedBioLevel = encodeURIComponent(this.selectedBiolevel || '');
        
        // Make AJAX request for suggestions with biological level context
        $.getJSON(`/suggest_pathways/${encodedKeId}?ke_title=${encodedKeTitle}&bio_level=${encodedBioLevel}&limit=8`)
            .done((data) => {
                console.log('Pathway suggestions loaded:', data);
                this.displayPathwaySuggestions(data);
            })
            .fail((xhr, status, error) => {
                console.error('Failed to load pathway suggestions:', error);
                this.showPathwaySuggestionsError('Failed to load pathway suggestions');
            });
    }

    showPathwaySuggestionsLoading() {
        // Remove existing suggestions
        $("#pathway-suggestions").remove();
        
        const loadingHtml = `
            <div id="pathway-suggestions" style="margin-top: 15px; padding: 15px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color: #29235C;">💡 Suggested Pathways</h3>
                <div style="display: flex; align-items: center; color: #666;">
                    <div style="margin-right: 10px;">🔄</div>
                    <span>Loading pathway suggestions...</span>
                </div>
            </div>
        `;
        
        // Insert after KE preview or KE dropdown
        if ($("#ke-preview").length) {
            $("#ke-preview").after(loadingHtml);
        } else {
            $("#ke_id").parent().after(loadingHtml);
        }
    }

    displayPathwaySuggestions(data) {
        // Remove existing suggestions
        $("#pathway-suggestions").remove();
        
        if (!data || data.total_suggestions === 0) {
            this.showNoSuggestions(data);
            return;
        }

        let suggestionsHtml = `
            <div id="pathway-suggestions" style="margin-top: 15px; padding: 15px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;">
                <h3 style="margin: 0 0 15px 0; color: #29235C;">💡 Suggested Pathways for Selected KE</h3>
        `;

        // Show gene information if available
        if (data.genes_found > 0) {
            suggestionsHtml += `
                <div style="margin-bottom: 15px; padding: 10px; background-color: #e3f2fd; border-radius: 4px; font-size: 14px;">
                    <strong>🧬 Associated Genes:</strong> ${data.gene_list.join(', ')} (${data.genes_found} gene${data.genes_found !== 1 ? 's' : ''} found)
                </div>
            `;
        }

        // Gene-based suggestions
        if (data.gene_based_suggestions && data.gene_based_suggestions.length > 0) {
            suggestionsHtml += `
                <div class="suggestion-section" style="margin-bottom: 15px;">
                    <h4 style="margin: 0 0 10px 0; color: #307BBF;">🎯 Gene-Based Matches (High Confidence)</h4>
                    <div class="suggestion-list">
            `;
            
            data.gene_based_suggestions.forEach(suggestion => {
                const geneOverlap = `${suggestion.matching_gene_count}/${data.genes_found} genes`;
                const confidenceBar = this.createConfidenceBar(suggestion.confidence_score);
                
                suggestionsHtml += `
                    <div class="suggestion-item" style="margin-bottom: 15px; padding: 12px; background-color: #ffffff; border: 1px solid #d4edda; border-radius: 6px; cursor: pointer; transition: all 0.2s ease;" 
                         onclick="window.KEWPApp.selectSuggestedPathway('${suggestion.pathwayID}', '${suggestion.pathwayTitle.replace(/'/g, "\\'")}')">
                        <div style="display: flex; gap: 12px; align-items: flex-start;">
                            <div style="flex: 1;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <strong style="color: #155724; font-size: 14px;">${suggestion.pathwayTitle}</strong>
                                    <div style="text-align: center;">
                                        ${confidenceBar}
                                        <div style="font-size: 10px; color: #666;">Confidence</div>
                                    </div>
                                </div>
                                <div style="font-size: 12px; color: #666; margin-bottom: 4px;">
                                    ID: ${suggestion.pathwayID} | Overlap: ${geneOverlap} (${Math.round(suggestion.gene_overlap_ratio * 100)}%)
                                </div>
                                <div style="font-size: 11px; color: #666; margin-bottom: 8px;">
                                    Matching genes: ${suggestion.matching_genes.join(', ')}
                                </div>
                                <button onclick="event.stopPropagation(); window.KEWPApp.showPathwayPreview('${suggestion.pathwayID}', '${suggestion.pathwayTitle.replace(/'/g, "\\'")}', '${suggestion.pathwaySvgUrl || ''}')" 
                                        style="font-size: 11px; padding: 4px 8px; background: #e3f2fd; border: 1px solid #307BBF; border-radius: 3px; color: #307BBF; cursor: pointer;">
                                    👁️ Preview Pathway
                                </button>
                            </div>
                            <div style="width: 140px; height: 120px; border: 1px solid #ddd; border-radius: 6px; background: #f8f9fa; display: flex; align-items: center; justify-content: center; overflow: hidden; cursor: pointer;" onclick="event.stopPropagation(); window.KEWPApp.showPathwayPreview('${suggestion.pathwayID}', '${suggestion.pathwayTitle.replace(/'/g, "\\'")}', '${suggestion.pathwaySvgUrl || ''}')">
                                <img src="${suggestion.pathwaySvgUrl || ''}" 
                                     style="max-width: 100%; max-height: 100%; object-fit: contain; transition: transform 0.2s ease;" 
                                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block'"
                                     onmouseover="this.style.transform='scale(1.05)'"
                                     onmouseout="this.style.transform='scale(1)'"
                                     alt="Pathway thumbnail">
                                <div style="display: none; font-size: 32px; color: #999;">🛤️</div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            suggestionsHtml += '</div></div>';
        }

        // Text-based suggestions
        if (data.text_based_suggestions && data.text_based_suggestions.length > 0) {
            suggestionsHtml += `
                <div class="suggestion-section">
                    <h4 style="margin: 0 0 10px 0; color: #307BBF;">📝 Text-Based Matches</h4>
                    <div class="suggestion-list">
            `;
            
            data.text_based_suggestions.forEach(suggestion => {
                const similarity = Math.round(suggestion.combined_similarity * 100);
                const confidenceBar = this.createConfidenceBar(suggestion.confidence_score);
                
                suggestionsHtml += `
                    <div class="suggestion-item" style="margin-bottom: 15px; padding: 12px; background-color: #ffffff; border: 1px solid #bee5eb; border-radius: 6px; cursor: pointer; transition: all 0.2s ease;"
                         onclick="window.KEWPApp.selectSuggestedPathway('${suggestion.pathwayID}', '${suggestion.pathwayTitle.replace(/'/g, "\\'")}')">
                        <div style="display: flex; gap: 12px; align-items: flex-start;">
                            <div style="flex: 1;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <strong style="color: #0c5460; font-size: 14px;">${suggestion.pathwayTitle}</strong>
                                    <div style="text-align: center;">
                                        ${confidenceBar}
                                        <div style="font-size: 10px; color: #666;">Confidence</div>
                                    </div>
                                </div>
                                <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
                                    ID: ${suggestion.pathwayID} | Text similarity: ${similarity}%
                                </div>
                                <button onclick="event.stopPropagation(); window.KEWPApp.showPathwayPreview('${suggestion.pathwayID}', '${suggestion.pathwayTitle.replace(/'/g, "\\'")}', '${suggestion.pathwaySvgUrl || ''}')" 
                                        style="font-size: 11px; padding: 4px 8px; background: #e3f2fd; border: 1px solid #307BBF; border-radius: 3px; color: #307BBF; cursor: pointer;">
                                    👁️ Preview Pathway
                                </button>
                            </div>
                            <div style="width: 140px; height: 120px; border: 1px solid #ddd; border-radius: 6px; background: #f8f9fa; display: flex; align-items: center; justify-content: center; overflow: hidden; cursor: pointer;" onclick="event.stopPropagation(); window.KEWPApp.showPathwayPreview('${suggestion.pathwayID}', '${suggestion.pathwayTitle.replace(/'/g, "\\'")}', '${suggestion.pathwaySvgUrl || ''}')">
                                <img src="${suggestion.pathwaySvgUrl || ''}" 
                                     style="max-width: 100%; max-height: 100%; object-fit: contain; transition: transform 0.2s ease;" 
                                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block'"
                                     onmouseover="this.style.transform='scale(1.05)'"
                                     onmouseout="this.style.transform='scale(1)'"
                                     alt="Pathway thumbnail">
                                <div style="display: none; font-size: 32px; color: #999;">🛤️</div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            suggestionsHtml += '</div></div>';
        }

        suggestionsHtml += `
                <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #dee2e6; font-size: 12px; color: #666; text-align: center;">
                    Click any suggestion to auto-select it in the pathway dropdown below
                </div>
            </div>
        `;

        // Insert after KE preview or KE dropdown
        if ($("#ke-preview").length) {
            $("#ke-preview").after(suggestionsHtml);
        } else {
            $("#ke_id").parent().after(suggestionsHtml);
        }
    }

    showNoSuggestions(data) {
        let message = "No pathway suggestions found for this Key Event.";
        let details = "";
        
        if (data && data.genes_found === 0) {
            details = "No associated genes were found in the AOP-Wiki RDF data.";
        } else if (data && data.genes_found > 0) {
            details = `Found ${data.genes_found} associated gene${data.genes_found !== 1 ? 's' : ''} (${data.gene_list.join(', ')}) but no matching pathways.`;
        }

        const noSuggestionsHtml = `
            <div id="pathway-suggestions" style="margin-top: 15px; padding: 15px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color: #29235C;">💡 Pathway Suggestions</h3>
                <div style="color: #666; text-align: center; padding: 20px;">
                    <div style="font-size: 32px; margin-bottom: 10px;">🔍</div>
                    <div style="margin-bottom: 8px;">${message}</div>
                    ${details ? `<div style="font-size: 12px; color: #888;">${details}</div>` : ''}
                    <div style="margin-top: 15px; font-size: 12px;">
                        💡 <em>Try using the search function below to find pathways manually</em>
                    </div>
                </div>
            </div>
        `;

        // Insert after KE preview or KE dropdown
        if ($("#ke-preview").length) {
            $("#ke-preview").after(noSuggestionsHtml);
        } else {
            $("#ke_id").parent().after(noSuggestionsHtml);
        }
    }

    showPathwaySuggestionsError(errorMessage) {
        // Remove existing suggestions
        $("#pathway-suggestions").remove();
        
        const errorHtml = `
            <div id="pathway-suggestions" style="margin-top: 15px; padding: 15px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color: #29235C;">💡 Pathway Suggestions</h3>
                <div style="color: #dc3545; text-align: center; padding: 20px;">
                    <div style="font-size: 32px; margin-bottom: 10px;">⚠️</div>
                    <div>${errorMessage}</div>
                    <div style="margin-top: 10px; font-size: 12px; color: #666;">
                        You can still browse pathways manually using the dropdown below
                    </div>
                </div>
            </div>
        `;
        
        // Insert after KE preview or KE dropdown
        if ($("#ke-preview").length) {
            $("#ke-preview").after(errorHtml);
        } else {
            $("#ke_id").parent().after(errorHtml);
        }
    }

    createConfidenceBar(score) {
        const percentage = Math.round(score * 100);
        let color = '#dc3545'; // red for low
        let bgColor = '#ffe6e6'; // light red background
        let textColor = '#dc3545';
        
        if (percentage >= 70) {
            color = '#28a745'; // green for high
            bgColor = '#e6ffe6'; // light green background
            textColor = '#28a745';
        } else if (percentage >= 40) {
            color = '#ffc107'; // yellow for medium  
            bgColor = '#fffde6'; // light yellow background
            textColor = '#856404';
        }
        
        return `
            <div style="
                width: 80px; 
                background-color: ${bgColor}; 
                border: 1px solid ${color}; 
                border-radius: 8px; 
                padding: 8px; 
                text-align: center; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            ">
                <div style="
                    width: 100%; 
                    height: 12px; 
                    background-color: #f0f0f0; 
                    border-radius: 6px; 
                    overflow: hidden; 
                    margin-bottom: 4px;
                    border: 1px solid #ddd;
                ">
                    <div style="
                        width: ${percentage}%; 
                        height: 100%; 
                        background: linear-gradient(135deg, ${color}, ${color}dd); 
                        transition: width 0.4s ease;
                        border-radius: 6px;
                    "></div>
                </div>
                <div style="
                    font-size: 14px; 
                    font-weight: bold; 
                    color: ${textColor};
                    text-shadow: 0 1px 2px rgba(255,255,255,0.8);
                ">${percentage}%</div>
            </div>
        `;
    }

    selectSuggestedPathway(pathwayId, pathwayTitle) {
        // Find the pathway option in the dropdown
        const $dropdown = $("#wp_id");
        const $option = $dropdown.find(`option[value="${pathwayId}"]`);
        
        if ($option.length > 0) {
            // Select the pathway
            $dropdown.val(pathwayId).trigger('change');
            console.log(`Selected suggested pathway: ${pathwayId} - ${pathwayTitle}`);
            
            // Show success message
            this.showMessage(`✅ Selected suggested pathway: ${pathwayTitle}`, "success");
            
            // Scroll to the pathway selection area
            $dropdown.get(0).scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
            console.error(`Pathway option not found in dropdown: ${pathwayId}`);
            this.showMessage(`⚠️ Pathway ${pathwayId} not found in dropdown. It may not be loaded yet.`, "warning");
        }
    }

    hidePathwaySuggestions() {
        $("#pathway-suggestions").remove();
    }

    setupPathwaySearch() {
        const $searchInput = $("#pathway-search");
        const $searchResults = $("#search-results");
        let searchTimeout;
        
        // Handle search input with debouncing
        $searchInput.on('input', (e) => {
            clearTimeout(searchTimeout);
            const query = $(e.target).val().trim();
            
            if (query.length < 2) {
                $searchResults.hide();
                return;
            }
            
            // Debounce search requests
            searchTimeout = setTimeout(() => {
                this.performPathwaySearch(query);
            }, 300);
        });
        
        // Handle focus/blur events
        $searchInput.on('focus', () => {
            if ($searchResults.children().length > 0) {
                $searchResults.show();
            }
        });
        
        $searchInput.on('blur', (e) => {
            // Delay hiding to allow for clicks on results
            setTimeout(() => {
                $searchResults.hide();
            }, 150);
        });
        
        // Handle keyboard navigation
        $searchInput.on('keydown', (e) => {
            const $items = $searchResults.find('.search-result-item');
            const $active = $items.filter('.active');
            
            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    if ($active.length === 0) {
                        $items.first().addClass('active');
                    } else {
                        $active.removeClass('active');
                        const $next = $active.next('.search-result-item');
                        if ($next.length > 0) {
                            $next.addClass('active');
                        } else {
                            $items.first().addClass('active');
                        }
                    }
                    break;
                    
                case 'ArrowUp':
                    e.preventDefault();
                    if ($active.length === 0) {
                        $items.last().addClass('active');
                    } else {
                        $active.removeClass('active');
                        const $prev = $active.prev('.search-result-item');
                        if ($prev.length > 0) {
                            $prev.addClass('active');
                        } else {
                            $items.last().addClass('active');
                        }
                    }
                    break;
                    
                case 'Enter':
                    e.preventDefault();
                    if ($active.length > 0) {
                        $active.click();
                    }
                    break;
                    
                case 'Escape':
                    $searchResults.hide();
                    $searchInput.blur();
                    break;
            }
        });
    }

    performPathwaySearch(query) {
        const $searchResults = $("#search-results");
        
        // Show loading
        $searchResults.html('<div style="padding: 10px; color: #666;">🔄 Searching...</div>').show();
        
        // Make search request
        $.getJSON(`/search_pathways?q=${encodeURIComponent(query)}&threshold=0.2&limit=10`)
            .done((data) => {
                this.displaySearchResults(data.results, query);
            })
            .fail((xhr, status, error) => {
                console.error('Search failed:', error);
                $searchResults.html('<div style="padding: 10px; color: #dc3545;">❌ Search failed. Please try again.</div>');
            });
    }

    displaySearchResults(results, query) {
        const $searchResults = $("#search-results");
        
        if (results.length === 0) {
            $searchResults.html(`
                <div style="padding: 15px; text-align: center; color: #666;">
                    <div style="margin-bottom: 8px;">🔍 No pathways found</div>
                    <div style="font-size: 12px;">Try different keywords or reduce specificity</div>
                </div>
            `).show();
            return;
        }
        
        let resultsHtml = '';
        results.forEach(result => {
            const relevancePercentage = Math.round(result.relevance_score * 100);
            const titleHighlighted = this.highlightSearchTerms(result.pathwayTitle, query);
            const descriptionSnippet = result.pathwayDescription 
                ? this.truncateText(result.pathwayDescription, 100) 
                : 'No description available';
            
            resultsHtml += `
                <div class="search-result-item" style="padding: 10px; border-bottom: 1px solid #eee; cursor: pointer; transition: background-color 0.2s;"
                     data-pathway-id="${result.pathwayID}" data-pathway-title="${result.pathwayTitle.replace(/"/g, '&quot;')}"
                     onmouseover="this.style.backgroundColor='#f8f9fa'"
                     onmouseout="this.classList.contains('active') || (this.style.backgroundColor='white')">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
                        <div style="flex: 1;">
                            <div style="font-weight: bold; color: #29235C; margin-bottom: 4px;">
                                ${titleHighlighted}
                            </div>
                            <div style="font-size: 11px; color: #666; margin-bottom: 4px;">
                                ID: ${result.pathwayID}
                            </div>
                            <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
                                ${descriptionSnippet}
                            </div>
                            <button onclick="event.stopPropagation(); window.KEWPApp.showPathwayPreview('${result.pathwayID}', '${result.pathwayTitle.replace(/'/g, "\\'")}', '${result.pathwaySvgUrl || ''}')" 
                                    style="font-size: 10px; padding: 3px 6px; background: #e3f2fd; border: 1px solid #307BBF; border-radius: 2px; color: #307BBF; cursor: pointer;">
                                👁️ Preview
                            </button>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div style="text-align: center;">
                                <div style="background-color: #e9ecef; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; color: #495057;">
                                    ${relevancePercentage}%
                                </div>
                                <div style="font-size: 9px; color: #666; margin-top: 2px;">match</div>
                            </div>
                            <div style="width: 60px; height: 45px; border: 1px solid #ddd; border-radius: 4px; background: #f8f9fa; display: flex; align-items: center; justify-content: center; overflow: hidden; cursor: pointer;" onclick="event.stopPropagation(); window.KEWPApp.showPathwayPreview('${result.pathwayID}', '${result.pathwayTitle.replace(/'/g, "\\'")}', '${result.pathwaySvgUrl || ''}')">
                                <img src="${result.pathwaySvgUrl || ''}" 
                                     style="max-width: 100%; max-height: 100%; object-fit: contain; transition: transform 0.2s ease;" 
                                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block'"
                                     onmouseover="this.style.transform='scale(1.05)'"
                                     onmouseout="this.style.transform='scale(1)'"
                                     alt="Pathway thumbnail">
                                <div style="display: none; font-size: 16px; color: #999;">🛤️</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        $searchResults.html(resultsHtml).show();
        
        // Add click handlers
        $searchResults.find('.search-result-item').on('click', (e) => {
            const $item = $(e.currentTarget);
            const pathwayId = $item.data('pathway-id');
            const pathwayTitle = $item.data('pathway-title');
            
            this.selectSearchResult(pathwayId, pathwayTitle);
        });
    }

    selectSearchResult(pathwayId, pathwayTitle) {
        // Clear search
        $("#pathway-search").val('');
        $("#search-results").hide();
        
        // Check if pathway exists in dropdown
        const $dropdown = $("#wp_id");
        const $option = $dropdown.find(`option[value="${pathwayId}"]`);
        
        if ($option.length > 0) {
            // Select the pathway
            $dropdown.val(pathwayId).trigger('change');
            console.log(`Selected pathway from search: ${pathwayId} - ${pathwayTitle}`);
            this.showMessage(`✅ Selected pathway: ${pathwayTitle}`, "success");
        } else {
            // Pathway not in dropdown - need to add it dynamically
            console.log(`Adding new pathway to dropdown: ${pathwayId} - ${pathwayTitle}`);
            
            // Add option to dropdown
            $dropdown.append(`<option value="${pathwayId}" data-title="${pathwayTitle}">${pathwayId} - ${pathwayTitle}</option>`);
            
            // Select the newly added pathway
            $dropdown.val(pathwayId).trigger('change');
            
            this.showMessage(`✅ Added and selected pathway: ${pathwayTitle}`, "success");
        }
    }

    highlightSearchTerms(text, query) {
        if (!query || query.length < 2) return text;
        
        const words = query.toLowerCase().split(/\s+/).filter(word => word.length > 1);
        let highlightedText = text;
        
        words.forEach(word => {
            const regex = new RegExp(`(${word})`, 'gi');
            highlightedText = highlightedText.replace(regex, '<mark style="background-color: #fff3cd; padding: 1px 2px;">$1</mark>');
        });
        
        return highlightedText;
    }

    truncateText(text, maxLength) {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    showPathwayPreview(pathwayID, pathwayTitle, svgUrl) {
        // Remove existing preview
        $("#pathway-preview-modal").remove();
        
        const modalHtml = `
            <div id="pathway-preview-modal" style="
                position: fixed; top: 0; left: 0; right: 0; bottom: 0; 
                background: rgba(0,0,0,0.8); z-index: 10000; 
                display: flex; align-items: center; justify-content: center;
                padding: 20px; box-sizing: border-box;">
                <div style="
                    background: white; border-radius: 12px; 
                    width: 95vw; max-width: 1400px; height: 95vh; max-height: 1000px;
                    display: flex; flex-direction: column;
                    box-shadow: 0 20px 50px rgba(0,0,0,0.4);">
                    
                    <!-- Header -->
                    <div style="
                        padding: 15px 20px; border-bottom: 1px solid #eee; 
                        display: flex; justify-content: space-between; align-items: center;
                        background: #f8f9fa; border-radius: 8px 8px 0 0;">
                        <div>
                            <h3 style="margin: 0; color: #29235C; font-size: 16px;">${pathwayTitle}</h3>
                            <div style="font-size: 12px; color: #666; margin-top: 4px;">ID: ${pathwayID}</div>
                        </div>
                        <button onclick="$('#pathway-preview-modal').remove()" 
                                style="
                                    background: none; border: none; font-size: 32px; 
                                    cursor: pointer; color: #666; padding: 0; width: 30px; height: 30px;
                                    display: flex; align-items: center; justify-content: center;
                                    border-radius: 50%; transition: background 0.2s;"
                                onmouseover="this.style.background='#e9ecef'"
                                onmouseout="this.style.background='none'">×</button>
                    </div>
                    
                    <!-- Content -->
                    <div style="
                        padding: 20px; overflow: auto; flex: 1;
                        display: flex; flex-direction: column; align-items: center;">
                        <div id="pathway-svg-container" style="
                            width: 100%; max-width: 1200px; text-align: center;
                            border: 1px solid #ddd; border-radius: 8px; 
                            padding: 20px; background: #fafafa; position: relative;
                            min-height: 400px;">
                            <div style="margin-bottom: 15px; color: #666;">Loading pathway diagram...</div>
                            <div class="loading-spinner" style="display: inline-block; font-size: 32px;">🔄</div>
                        </div>
                        
                        <!-- Action buttons -->
                        <div style="margin-top: 20px; display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;">
                            <button onclick="window.KEWPApp.selectSuggestedPathway('${pathwayID}', '${pathwayTitle.replace(/'/g, "\\'")}'); $('#pathway-preview-modal').remove();" 
                                    style="
                                        padding: 8px 16px; background: #307BBF; color: white; 
                                        border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">
                                ✅ Select This Pathway
                            </button>
                            <a href="https://www.wikipathways.org/index.php/Pathway:${pathwayID}" 
                               target="_blank" 
                               style="
                                    padding: 8px 16px; background: #f8f9fa; color: #307BBF; 
                                    border: 1px solid #307BBF; border-radius: 4px; 
                                    text-decoration: none; font-size: 14px; display: inline-block;">
                                🔗 View on WikiPathways
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $("body").append(modalHtml);
        
        // Load the SVG
        if (svgUrl) {
            this.loadPathwaySvg(svgUrl, pathwayID);
        } else {
            $("#pathway-svg-container").html(`
                <div style="color: #666; padding: 40px;">
                    <div style="font-size: 48px; margin-bottom: 15px;">🛤️</div>
                    <div>Pathway diagram not available</div>
                    <div style="font-size: 12px; margin-top: 8px;">
                        You can view the pathway on WikiPathways using the link below
                    </div>
                </div>
            `);
        }
        
        // Close on background click
        $("#pathway-preview-modal").on('click', (e) => {
            if (e.target.id === 'pathway-preview-modal') {
                $("#pathway-preview-modal").remove();
            }
        });
        
        // Close on Escape key
        $(document).on('keydown.pathway-preview', (e) => {
            if (e.key === 'Escape') {
                $("#pathway-preview-modal").remove();
                $(document).off('keydown.pathway-preview');
            }
        });
    }

    loadPathwaySvg(svgUrl, pathwayID) {
        const $container = $("#pathway-svg-container");
        
        // Try to load SVG with error handling
        const img = new Image();
        
        img.onload = function() {
            // Calculate aspect ratio for responsive scaling
            const aspectRatio = this.naturalWidth / this.naturalHeight;
            const isWide = aspectRatio > 1.5;
            const isTall = aspectRatio < 0.7;
            
            // Set container size based on image shape
            let containerWidth = isWide ? '100%' : (isTall ? '60%' : '80%');
            let containerHeight = isTall ? '70vh' : (isWide ? '50vh' : '60vh');
            
            $container.html(`
                <div style="margin-bottom: 15px; font-weight: bold; color: #29235C; text-align: center;">
                    ${pathwayID} Pathway Diagram
                    <div style="font-size: 12px; color: #666; font-weight: normal; margin-top: 4px;">
                        Original size: ${this.naturalWidth} × ${this.naturalHeight}px
                    </div>
                </div>
                
                <!-- Zoom Controls -->
                <div style="text-align: center; margin-bottom: 15px;">
                    <button id="zoom-out" style="padding: 6px 12px; margin: 0 3px; background: #f8f9fa; border: 1px solid #666; border-radius: 4px; cursor: pointer; color: #333;">🔍−</button>
                    <button id="zoom-reset" style="padding: 6px 12px; margin: 0 3px; background: #f8f9fa; border: 1px solid #666; border-radius: 4px; cursor: pointer; color: #333;">100%</button>
                    <button id="zoom-in" style="padding: 6px 12px; margin: 0 3px; background: #f8f9fa; border: 1px solid #666; border-radius: 4px; cursor: pointer; color: #333;">🔍+</button>
                    <button id="fit-width" style="padding: 6px 12px; margin: 0 3px; background: #307BBF; border: 1px solid #307BBF; border-radius: 4px; cursor: pointer; color: white;">Fit Width</button>
                </div>
                
                <div id="svg-viewport" style="
                    overflow: auto; 
                    width: ${containerWidth}; 
                    height: ${containerHeight};
                    border: 1px solid #ddd; 
                    border-radius: 8px; 
                    background: white;
                    margin: 0 auto;
                    position: relative;
                    cursor: grab;
                ">
                    <img id="pathway-svg-img" src="${svgUrl}" 
                         alt="Pathway ${pathwayID}" 
                         style="
                            display: block;
                            max-width: none;
                            height: auto;
                            width: auto;
                            transition: transform 0.3s ease;
                            user-select: none;
                         "
                         draggable="false">
                </div>
                
                <div style="font-size: 11px; color: #666; margin-top: 12px; text-align: center;">
                    Source: WikiPathways.org<br>
                    💡 Use zoom controls above or scroll wheel to zoom • Click and drag to pan
                </div>
            `);
            
            // Add zoom and pan functionality
            window.KEWPApp.setupImageZoomPan('pathway-svg-img', 'svg-viewport');
        };
        
        img.onerror = function() {
            console.warn(`Failed to load pathway SVG: ${svgUrl}`);
            
            // Fallback: try to load as object/iframe
            $container.html(`
                <div style="margin-bottom: 10px; font-weight: bold; color: #29235C;">
                    ${pathwayID} Pathway Diagram
                </div>
                <div style="position: relative; border: 1px solid #ddd; border-radius: 4px; background: white;">
                    <object data="${svgUrl}" 
                            type="image/svg+xml" 
                            style="width: 100%; height: 600px; border: none;"
                            onload="console.log('SVG loaded as object')">
                        <div style="padding: 40px; text-align: center; color: #666;">
                            <div style="font-size: 48px; margin-bottom: 15px;">⚠️</div>
                            <div>Unable to load pathway diagram</div>
                            <div style="font-size: 12px; margin-top: 8px;">
                                The diagram may not be available or there might be a connection issue.<br>
                                Try viewing it directly on WikiPathways.
                            </div>
                        </div>
                    </object>
                </div>
                <div style="font-size: 11px; color: #666; margin-top: 8px;">
                    Source: WikiPathways.org
                </div>
            `);
        };
        
        // Start loading the image
        img.src = svgUrl;
    }

    setupImageZoomPan(imgId, viewportId) {
        const $img = $(`#${imgId}`);
        const $viewport = $(`#${viewportId}`);
        
        let scale = 1;
        let isPanning = false;
        let lastX = 0;
        let lastY = 0;
        
        // Initial setup - fit to container width
        setTimeout(() => {
            const img = $img[0];
            const viewport = $viewport[0];
            
            if (img && viewport) {
                const containerWidth = $viewport.width();
                const imgWidth = img.naturalWidth;
                
                if (imgWidth > containerWidth) {
                    scale = containerWidth / imgWidth * 0.95;
                    $img.css('transform', `scale(${scale})`);
                }
                
                // Update zoom reset button text
                $('#zoom-reset').text(`${Math.round(scale * 100)}%`);
            }
        }, 100);
        
        // Zoom controls
        $('#zoom-in').on('click', () => {
            scale = Math.min(scale * 1.25, 5);
            $img.css('transform', `scale(${scale})`);
            $('#zoom-reset').text(`${Math.round(scale * 100)}%`);
        });
        
        $('#zoom-out').on('click', () => {
            scale = Math.max(scale / 1.25, 0.1);
            $img.css('transform', `scale(${scale})`);
            $('#zoom-reset').text(`${Math.round(scale * 100)}%`);
        });
        
        $('#zoom-reset').on('click', () => {
            scale = 1;
            $img.css('transform', 'scale(1)');
            $('#zoom-reset').text('100%');
            $viewport.scrollLeft(0).scrollTop(0);
        });
        
        $('#fit-width').on('click', () => {
            const containerWidth = $viewport.width();
            const imgWidth = $img[0].naturalWidth;
            scale = containerWidth / imgWidth * 0.95;
            $img.css('transform', `scale(${scale})`);
            $('#zoom-reset').text(`${Math.round(scale * 100)}%`);
            $viewport.scrollLeft(0).scrollTop(0);
        });
        
        // Mouse wheel zoom
        $viewport.on('wheel', (e) => {
            e.preventDefault();
            const delta = e.originalEvent.deltaY;
            const zoomFactor = delta > 0 ? 0.9 : 1.1;
            
            scale = Math.min(Math.max(scale * zoomFactor, 0.1), 5);
            $img.css('transform', `scale(${scale})`);
            $('#zoom-reset').text(`${Math.round(scale * 100)}%`);
        });
        
        // Pan functionality
        $img.on('mousedown', (e) => {
            isPanning = true;
            lastX = e.clientX;
            lastY = e.clientY;
            $viewport.css('cursor', 'grabbing');
            e.preventDefault();
        });
        
        $(document).on('mousemove', (e) => {
            if (isPanning) {
                const deltaX = e.clientX - lastX;
                const deltaY = e.clientY - lastY;
                
                $viewport.scrollLeft($viewport.scrollLeft() - deltaX);
                $viewport.scrollTop($viewport.scrollTop() - deltaY);
                
                lastX = e.clientX;
                lastY = e.clientY;
            }
        });
        
        $(document).on('mouseup', () => {
            if (isPanning) {
                isPanning = false;
                $viewport.css('cursor', 'grab');
            }
        });
        
        // Touch support for mobile
        let lastTouchDistance = 0;
        
        $viewport.on('touchstart', (e) => {
            if (e.originalEvent.touches.length === 2) {
                const touch1 = e.originalEvent.touches[0];
                const touch2 = e.originalEvent.touches[1];
                lastTouchDistance = Math.sqrt(
                    Math.pow(touch2.clientX - touch1.clientX, 2) +
                    Math.pow(touch2.clientY - touch1.clientY, 2)
                );
            }
        });
        
        $viewport.on('touchmove', (e) => {
            if (e.originalEvent.touches.length === 2) {
                e.preventDefault();
                const touch1 = e.originalEvent.touches[0];
                const touch2 = e.originalEvent.touches[1];
                const currentDistance = Math.sqrt(
                    Math.pow(touch2.clientX - touch1.clientX, 2) +
                    Math.pow(touch2.clientY - touch1.clientY, 2)
                );
                
                if (lastTouchDistance > 0) {
                    const scaleFactor = currentDistance / lastTouchDistance;
                    scale = Math.min(Math.max(scale * scaleFactor, 0.1), 5);
                    $img.css('transform', `scale(${scale})`);
                    $('#zoom-reset').text(`${Math.round(scale * 100)}%`);
                }
                
                lastTouchDistance = currentDistance;
            }
        });
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