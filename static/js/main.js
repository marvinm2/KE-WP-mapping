/**
 * Main JavaScript functionality for KE-WP Mapping Application
 */

class KEWPApp {
    constructor() {
        this.isLoggedIn = false;
        this.csrfToken = null;
        this.stepAnswers = {};
        this.scoringConfig = null;
        this.configLoaded = false;

        // Load scoring config first, then initialize
        this.loadScoringConfig().then(() => {
            this.init();
        });
    }

    async loadScoringConfig() {
        try {
            const response = await fetch('/api/scoring-config');
            if (response.ok) {
                const data = await response.json();
                this.scoringConfig = data.ke_pathway_assessment;
                this.configLoaded = true;
                console.log('Scoring configuration loaded:', data.metadata);
            } else {
                throw new Error('Failed to fetch config');
            }
        } catch (error) {
            console.warn('Failed to load scoring config, using defaults:', error);
            this.scoringConfig = this.getDefaultScoringConfig();
            this.configLoaded = true;
        }
    }

    getDefaultScoringConfig() {
        // Return current hardcoded values as fallback
        return {
            evidence_quality: { known: 3, likely: 2, possible: 1, uncertain: 0 },
            pathway_specificity: { specific: 2, includes: 1, loose: 0 },
            ke_coverage: { complete: 1.5, keysteps: 1.0, minor: 0.5 },
            biological_level: {
                bonus: 1.0,
                qualifying_levels: ['molecular', 'cellular', 'tissue']
            },
            confidence_thresholds: { high: 5.0, medium: 2.5 },
            max_scores: {
                with_bio_bonus: 7.5,
                without_bio_bonus: 6.5
            }
        };
    }

    init() {
        this.setupCSRF();
        this.setupEventListeners();
        this.loadDropdownOptions();
        this.loadDataVersions();

        // Initialize form validation

        // Restore form state if returning from login
        this.restoreFormState();
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
        
        // CSRF token configured successfully
    }

    setupEventListeners() {
        // Retrieve login status
        this.isLoggedIn = $("body").data("is-logged-in") === true;
        // User login status retrieved

        // Form submission handler
        $("#mapping-form").on('submit', (e) => {
            this.handleFormSubmission(e);
        });

        // Confidence assessment handlers
        $(document).on("click", ".btn-group .btn-option", (e) => this.handleConfidenceAssessment(e));

        // Dropdown change handlers
        $("#ke_id").on('change', () => this.toggleAssessmentSection());
        
        // KE selection change handler for preview
        $("#ke_id").on('change', (e) => this.handleKESelection(e));
        
        // Setup pathway event handlers
        this.setupPathwayEventHandlers();
        
        // Assessment completion handler
        $(document).on('click', '#complete-all-assessments', () => this.handleCompleteAllAssessments());
        
        // Pathway search functionality
        this.setupPathwaySearch();
        
        // Direct button click handler fallback
        $("#mapping-form button[type='submit']").on('click', (e) => {
            e.preventDefault();
            $("#mapping-form").trigger('submit');
        });
        
        // Save form state before login (using delegation)
        $(document).on('click', 'a[href*="/login"]', (e) => {
            this.saveFormState();
        });
    }

    loadDropdownOptions() {
        this.loadKEOptions();
        this.loadPathwayOptions();
    }

    loadKEOptions() {
        $.getJSON("/get_ke_options")
            .done((data) => {

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

                // Initialize Select2 for searchable dropdown
                dropdown.select2({
                    placeholder: 'Search for a Key Event...',
                    allowClear: true,
                    width: '100%',
                    matcher: this.customMatcher
                });
            })
            .fail((xhr, status, error) => {
                console.error("Failed to load KE options:", error);
                const errorMsg = xhr.responseJSON?.error || "Unable to load Key Events. Please check your internet connection and try refreshing the page.";
                this.showMessage(errorMsg, "error");
            });
    }

    customMatcher(params, data) {
        // If there are no search terms, return all data
        if ($.trim(params.term) === '') {
            return data;
        }

        // Do not display the item if there is no 'text' property
        if (typeof data.text === 'undefined') {
            return null;
        }

        // Search term matching - case insensitive, matches anywhere in text
        const searchTerm = params.term.toLowerCase();
        const text = data.text.toLowerCase();

        // Match if search term is found in the text
        if (text.indexOf(searchTerm) > -1) {
            return data;
        }

        // Return null if term not found
        return null;
    }

    loadPathwayOptions() {
        $.getJSON("/get_pathway_options")
            .done((data) => {
                
                // Sort data by Pathway ID numerically
                data.sort((a, b) => {
                    const matchA = a.pathwayID.match(/\d+/);
                    const matchB = b.pathwayID.match(/\d+/);
                    const idA = matchA ? parseInt(matchA[0]) : 0;
                    const idB = matchB ? parseInt(matchB[0]) : 0;
                    return idA - idB;
                });

                // Store pathway options for later use
                this.pathwayOptions = data;
                
                // Populate all pathway dropdowns
                this.populatePathwayDropdowns();
            })
            .fail((xhr, status, error) => {
                console.error("Failed to load Pathway options:", error);
                const errorMsg = xhr.responseJSON?.error || "Unable to load Pathways. Please check your internet connection and try refreshing the page.";
                this.showMessage(errorMsg, "error");
            });
    }

    handleFormSubmission(event) {
        event.preventDefault();

        // Get pathway title from the actual visible dropdown, not the hidden input
        const selectedPathwayOption = $("select[name='wp_id'] option:selected").first();
        const wpTitle = selectedPathwayOption.data("title") || selectedPathwayOption.text() || $("#wp_id").val();
        
        const formData = {
            ke_id: $("#ke_id").val(),
            ke_title: $("#ke_id option:selected").data("title"),
            wp_id: $("#wp_id").val(),
            wp_title: wpTitle,
            connection_type: this.mapConnectionTypeForServer($("#connection_type").val()),
            confidence_level: $("#confidence_level").val(),
            csrf_token: this.csrfToken
        };

        // Form data prepared for submission
        console.log('Form submission debug:', {
            formData: formData,
            selectedPathwayOption: selectedPathwayOption.text(),
            originalConnectionType: $("#connection_type").val(),
            mappedConnectionType: formData.connection_type
        });

        // Validate required fields
        if (!formData.ke_id || !formData.wp_id) {
            this.showMessage("Please select both a Key Event and at least one Pathway before submitting.", "error");
            return;
        }

        // Check if we have multiple pathways (from multi-pathway assessment)
        if (this.multiPathwayResults && this.multiPathwayResults.length > 1) {
            this.handleMultiPathwaySubmission();
            return;
        }

        // Single pathway submission - existing logic
        if (!formData.connection_type || !formData.confidence_level) {
            this.showMessage("Please complete the confidence assessment for all selected pathways before submitting.", "error");
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
                const errorMsg = xhr.responseJSON?.error || "Unable to verify mapping. Please try again or contact support if the problem persists.";
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
                <h3>New Mapping Preview</h3>
                <p>Review your new mapping that will be added:</p>
                
                <div class="mapping-preview" style="display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 20px; margin: 20px 0; width: 100%;">
                    <div class="preview-section ke-section preview-section-ke">
                        <h4 class="preview-header-ke">Key Event Information</h4>
                        <p><strong>KE ID:</strong> ${formData.ke_id}</p>
                        <p><strong>KE Title:</strong> ${formData.ke_title}</p>
                        <p><strong>Biological Level:</strong> <span style="background-color: #e3f2fd; padding: 2px 6px; border-radius: 3px;">${biolevel || 'Not specified'}</span></p>
                        <div><strong>Description:</strong><br/>${keDescHtml}</div>
                    </div>
                    
                    <div class="preview-section wp-section preview-section-wp">
                        <h4 class="preview-header-wp">Pathway Information</h4>
                        <p><strong>WP ID:</strong> ${formData.wp_id}</p>
                        <p><strong>WP Title:</strong> ${formData.wp_title}</p>
                        <div><strong>Description:</strong><br/>${pwDescHtml}</div>
                    </div>
                </div>
                
                <div class="preview-section preview-section-metadata">
                    <h4 class="preview-header-metadata">Mapping Metadata</h4>
                    <div class="grid-two-column">
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
                
                <div class="confirmation-section">
                    <p class="confirmation-title"><strong>Do you want to add this new KE-WP mapping?</strong></p>
                    <p class="confirmation-subtitle">This will be added alongside the existing mappings shown above.</p>
                    <button id="confirm-submit" class="btn-success-custom">Yes, Add Entry</button>
                    <button id="cancel-submit" class="btn-secondary-custom">Cancel</button>
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
                <h3>Mapping Preview & Confirmation</h3>
                <p>Please carefully review your mapping details before submitting:</p>
                
                <div class="mapping-preview" style="display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 20px; margin: 20px 0; width: 100%;">
                    <div class="preview-section ke-section preview-section-ke">
                        <h4 class="preview-header-ke">Key Event Information</h4>
                        <p><strong>KE ID:</strong> ${formData.ke_id}</p>
                        <p><strong>KE Title:</strong> ${formData.ke_title}</p>
                        <p><strong>Biological Level:</strong> <span style="background-color: #e3f2fd; padding: 2px 6px; border-radius: 3px;">${biolevel || 'Not specified'}</span></p>
                        <div><strong>Description:</strong><br/>${keDescHtml}</div>
                    </div>
                    
                    <div class="preview-section wp-section preview-section-wp">
                        <h4 class="preview-header-wp">Pathway Information</h4>
                        <p><strong>WP ID:</strong> ${formData.wp_id}</p>
                        <p><strong>WP Title:</strong> ${formData.wp_title}</p>
                        <div><strong>Description:</strong><br/>${pwDescHtml}</div>
                    </div>
                </div>
                
                <div class="preview-section preview-section-metadata">
                    <h4 class="preview-header-metadata">Mapping Metadata</h4>
                    <div class="grid-two-column">
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
                
                <div class="confirmation-section">
                    <p class="confirmation-title"><strong>Are you sure you want to submit this mapping?</strong></p>
                    <p class="confirmation-subtitle">This action will add the mapping to the database and make it available for other researchers.</p>
                    <button id="confirm-final-submit" class="btn-success-custom">Yes, Submit Mapping</button>
                    <button id="cancel-final-submit" class="btn-secondary-custom">Cancel</button>
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
        // Check authentication before submitting
        if (!this.isLoggedIn) {
            this.showMessage("Please log in with GitHub to submit mappings.", "error");
            setTimeout(() => {
                // Save form state before redirecting to login
                this.saveFormState();
                window.location.href = '/auth/login';
            }, 2000);
            return;
        }
        
        // Show loading state
        this.showMessage("Submitting your mapping...", "info");
        
        // Handle multiple pathway IDs
        const pathwayIds = formData.wp_id.split(',').filter(id => id.trim());
        
        console.log('Submitting form data:', formData);
        console.log('Number of pathways:', pathwayIds.length);
        
        if (pathwayIds.length === 1) {
            // Single pathway - use existing logic
            $.post("/submit", formData)
                .done((response) => {
                    console.log('Submission successful:', response);
                    this.showSuccessMessage(response.message, formData);
                    $("#existing-entries").html("");
                    this.resetForm();
                })
                .fail((xhr) => {
                    console.error('Submission failed:', xhr);
                    console.log('Status:', xhr.status, 'Response:', xhr.responseText);
                    
                    if (xhr.status === 401 || xhr.status === 403) {
                        this.showMessage("Please log in to submit mappings.", "error");
                        setTimeout(() => {
                            this.saveFormState();
                            window.location.href = '/auth/login';
                        }, 2000);
                    } else {
                        const errorMsg = xhr.responseJSON?.error || "Unable to submit mapping. Please try again or check your internet connection.";
                        this.showMessage(errorMsg, "error");
                    }
                });
        } else {
            // Multiple pathways - submit each separately
            this.submitMultiplePathways(formData, pathwayIds);
        }
    }

    async submitMultiplePathways(baseFormData, pathwayIds) {
        let successCount = 0;
        let failureCount = 0;
        const errors = [];
        
        // Show loading state for multiple pathway submission
        const loadingHtml = `
            <div class="loading-container">
                <div class="loading-title">
                    Submitting Multiple Pathway Mappings
                </div>
                <div class="loading-subtitle">
                    Processing ${pathwayIds.length} pathway mapping(s)...
                </div>
                <div style="display: inline-block; width: 30px; height: 30px; border: 3px solid #f3f3f3; border-top: 3px solid #307BBF; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <div id="submission-progress" class="loading-progress">
                    Preparing submissions...
                </div>
            </div>
        `;
        $("#existing-entries").html(loadingHtml);
        
        for (const pathwayId of pathwayIds) {
            // Update progress
            $("#submission-progress").text(`Processing pathway ${successCount + failureCount + 1} of ${pathwayIds.length}: ${pathwayId}`);
            
            // Get pathway title for this ID
            const pathwayOption = this.pathwayOptions.find(opt => opt.pathwayID === pathwayId.trim());
            const pathwayTitle = pathwayOption ? pathwayOption.pathwayTitle : pathwayId;
            
            // Create individual submission
            const individualFormData = {
                ...baseFormData,
                wp_id: pathwayId.trim(),
                wp_title: pathwayTitle
            };
            
            try {
                await new Promise((resolve, reject) => {
                    $.post("/submit", individualFormData)
                        .done(() => {
                            successCount++;
                            $("#submission-progress").text(`Successfully submitted ${successCount} of ${pathwayIds.length} mappings`);
                            resolve();
                        })
                        .fail((xhr) => {
                            failureCount++;
                            const errorMsg = xhr.responseJSON?.error || `Unable to submit mapping for ${pathwayId}. Please try again.`;
                            errors.push(`${pathwayId}: ${errorMsg}`);
                            $("#submission-progress").text(`Completed ${successCount + failureCount} of ${pathwayIds.length} mappings (${failureCount} failed)`);
                            reject();
                        });
                });
                
                // Small delay to show progress
                await new Promise(resolve => setTimeout(resolve, 200));
            } catch (e) {
                // Error already handled above
            }
        }
        
        // Show summary message
        if (successCount > 0 && failureCount === 0) {
            this.showMessage(`Successfully submitted ${successCount} mapping(s)!`, "success");
            $("#existing-entries").html("");
            this.resetForm();
        } else if (successCount > 0 && failureCount > 0) {
            this.showMessage(`Successfully submitted ${successCount} mapping(s), but ${failureCount} failed. Please review the errors and try again for the failed mappings.`, "warning");
        } else {
            this.showMessage(`All mapping submissions failed. Please check your internet connection and try again. If the problem persists, contact support.`, "error");
        }
    }

    handleConfidenceAssessment(event) {
        const $btn = $(event.target);
        const $group = $btn.closest(".btn-group");
        const stepId = $group.data("step");
        const assessmentId = $group.data("assessment");
        const selectedValue = $btn.data("value");
        const $pathwayAssessment = $btn.closest(".pathway-assessment");
        const pathwayId = $pathwayAssessment.data("pathway-id");

        // Initialize pathway-specific answers if not exists
        if (!this.pathwayAssessments) {
            this.pathwayAssessments = {};
        }
        if (!this.pathwayAssessments[pathwayId]) {
            this.pathwayAssessments[pathwayId] = {};
        }

        // Save the value for this specific pathway
        this.pathwayAssessments[pathwayId][stepId] = selectedValue;
        
        // Debug logging
        console.log('handleConfidenceAssessment debug:', {
            stepId: stepId,
            selectedValue: selectedValue,
            pathwayId: pathwayId,
            currentAnswers: this.pathwayAssessments[pathwayId]
        });

        // Update UI
        $group.find(".btn-option").removeClass("selected");
        $btn.addClass("selected");

        // Show/hide next steps based on logic
        this.handlePathwayStepProgression($pathwayAssessment, pathwayId);
        
        // Update overall assessment status
        this.updateAssessmentStatus();
    }

    handlePathwayStepProgression($pathwayAssessment, pathwayId) {
        const answers = this.pathwayAssessments[pathwayId];
        const s1 = answers["step1"];  // Relationship type
        const s2 = answers["step2"];  // Evidence quality
        const s3 = answers["step3"];  // Pathway specificity
        const s4 = answers["step4"];  // Coverage comprehensiveness

        // Debug logging
        console.log('handlePathwayStepProgression debug:', {
            pathwayId: pathwayId,
            answers: answers,
            s1, s2, s3, s4
        });

        // Find steps within this pathway assessment
        const $steps = $pathwayAssessment.find(".assessment-step");

        // Reset visibility for new 4-step workflow
        $steps.filter("[data-step='step2'], [data-step='step3'], [data-step='step4']").hide();

        if (s1) {
            $steps.filter("[data-step='step2']").show();

            if (s2) {
                $steps.filter("[data-step='step3']").show();

                if (s3) {
                    $steps.filter("[data-step='step4']").show();

                    if (s4) {
                        // Complete assessment for this pathway
                        this.evaluatePathwayConfidence($pathwayAssessment, pathwayId);
                    }
                }
            }
        }
    }

    evaluatePathwayConfidence($pathwayAssessment, pathwayId) {
        const answers = this.pathwayAssessments[pathwayId];
        const config = this.scoringConfig;

        console.log('evaluatePathwayConfidence called:', {
            pathwayId: pathwayId,
            answers: answers,
            $pathwayAssessment: $pathwayAssessment
        });

        // Use existing confidence evaluation logic
        let baseScore = 0;
        let connectionType = "undefined";

        // Connection type from step 1 (now first question)
        connectionType = answers["step1"] || "unclear";

        // Evidence quality scoring (now step 2) - use config
        baseScore += config.evidence_quality[answers["step2"]] || 0;

        // Pathway specificity scoring (now step 3) - use config
        baseScore += config.pathway_specificity[answers["step3"]] || 0;

        // Coverage comprehensiveness scoring (now step 4) - use config
        baseScore += config.ke_coverage[answers["step4"]] || 0;

        // Apply biological level bonus - use config
        const bioLevel = this.selectedBiolevel ? this.selectedBiolevel.toLowerCase() : '';
        const qualifyingLevels = config.biological_level.qualifying_levels;
        const isMolecularLevel = qualifyingLevels.some(level => bioLevel.includes(level));

        if (isMolecularLevel) {
            baseScore += config.biological_level.bonus;
        }

        // Determine confidence level - use config thresholds
        let confidence;
        if (baseScore >= config.confidence_thresholds.high) {
            confidence = "high";
        } else if (baseScore >= config.confidence_thresholds.medium) {
            confidence = "medium";
        } else {
            confidence = "low";
        }

        // Update pathway assessment result - use config max scores
        const $result = $pathwayAssessment.find(".assessment-result");
        const maxScore = isMolecularLevel ?
            config.max_scores.with_bio_bonus :
            config.max_scores.without_bio_bonus;

        $result.find(".confidence-result").text(`${confidence} confidence`);
        $result.find(".connection-result").text(connectionType);
        $result.find(".score-details").text(`Score: ${baseScore.toFixed(1)}/${maxScore}${isMolecularLevel ? ' with biological level bonus' : ''}`);
        $result.show();

        // Store results for submission
        if (!this.pathwayResults) {
            this.pathwayResults = {};
        }
        this.pathwayResults[pathwayId] = {
            confidence: confidence,
            connection_type: connectionType,
            score: baseScore,
            answers: answers
        };

        console.log('evaluatePathwayConfidence completed:', {
            pathwayId: pathwayId,
            confidence: confidence,
            connectionType: connectionType,
            baseScore: baseScore,
            resultShown: $result.is(':visible')
        });
    }

    handleStepProgression() {
        const s1 = this.stepAnswers["step1"];  // Relationship type
        const s2 = this.stepAnswers["step2"];  // Evidence quality
        const s3 = this.stepAnswers["step3"];  // Pathway specificity
        const s4 = this.stepAnswers["step4"];  // Coverage comprehensiveness

        // Reset visibility for new 4-step workflow
        $("#step2, #step3, #step4").hide();
        $("#evaluateBtn").hide();

        if (s1) {
            $("#step2").show();
        }

        if (s2) {
            $("#step3").show();
        }

        if (s3) {
            $("#step4").show();
        }

        // Check if all required steps are completed
        const ready = s1 && s2 && s3 && s4;
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
        
        // Key Event selected
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
        const $select = $(event.target);
        const $group = $select.closest('.pathway-selection-group');
        const $pathwayInfo = $group.find('.pathway-info');
        
        const selectedOption = $select.find('option:selected');
        const title = selectedOption.data('title') || '';
        const description = selectedOption.data('description') || '';
        const svgUrl = selectedOption.data('svg-url') || '';
        const pathwayId = selectedOption.val();
        
        // Show pathway information within the group
        if (title) {
            this.showPathwayInfoInGroup($pathwayInfo, pathwayId, title, description, svgUrl);
        } else {
            $pathwayInfo.hide();
        }
        
        // Pathway selected
    }

    showPathwayInfoInGroup($container, pathwayId, title, description, svgUrl) {
        // Create collapsible description HTML
        const descriptionHTML = this.createCollapsibleDescription(description, `pathway-description-${pathwayId}`);
        
        // Create figure preview HTML (smaller for inline display)
        const figureHTML = svgUrl ? `
            <div style="margin: 10px 0; text-align: center;">
                <div style="border: 1px solid #ddd; border-radius: 4px; padding: 8px; background: white; display: inline-block;">
                    <img src="${svgUrl}" 
                         style="max-width: 200px; max-height: 120px; object-fit: contain; cursor: pointer;" 
                         onclick="window.KEWPApp.showPathwayPreview('${pathwayId}', '${title.replace(/'/g, "\\'")}', '${svgUrl}')"
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block'"
                         onload="this.style.display='block'; this.nextElementSibling.style.display='none'"
                         alt="Pathway diagram">
                    <div style="display: none; color: #666; font-style: italic; padding: 15px; font-size: 12px;">
                        Diagram not available
                    </div>
                </div>
                <div style="margin-top: 5px; font-size: 11px; color: #666;">
                    Click to enlarge
                </div>
            </div>
        ` : '';
        
        // Create preview HTML
        const infoHTML = `
            <div style="border-top: 1px solid #e2e8f0; margin-top: 10px; padding-top: 10px;">
                <h5 style="margin: 0 0 8px 0; color: #29235C; font-size: 14px;">Pathway: ${title}</h5>
                <div style="font-size: 12px; color: #666; margin-bottom: 8px;">ID: ${pathwayId}</div>
                ${description ? `<div style="margin-bottom: 10px; font-size: 13px;">${descriptionHTML}</div>` : '<div style="margin-bottom: 10px; color: #999; font-style: italic; font-size: 13px;">No description available</div>'}
                ${figureHTML}
            </div>
        `;
        
        $container.html(infoHTML).show();
    }

    showPathwayDetails(title, description, svgUrl = '') {
        // Remove existing preview
        $("#pathway-preview").remove();
        
        // Create collapsible description HTML
        const descriptionHTML = this.createCollapsibleDescription(description, 'pathway-description');
        
        // Create figure preview HTML
        const figureHTML = svgUrl ? `
            <div style="margin: 10px 0;">
                <strong>Pathway Diagram Preview:</strong>
                <div style="margin-top: 8px; text-align: center; border: 1px solid #ddd; border-radius: 4px; padding: 10px; background: white;">
                    <img src="${svgUrl}" 
                         style="max-width: 300px; max-height: 200px; object-fit: contain; cursor: pointer;" 
                         onclick="window.KEWPApp.showPathwayPreview($('#wp_id').val(), '${title.replace(/'/g, "\\'")}', '${svgUrl}')"
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block'"
                         onload="this.style.display='block'; this.nextElementSibling.style.display='none'"
                         alt="Pathway diagram">
                    <div style="display: none; color: #666; font-style: italic; padding: 20px;">
                        Pathway diagram not available
                    </div>
                </div>
                <div style="margin-top: 5px; font-size: 11px; color: #666;">
                    Click diagram to view full size
                </div>
            </div>
        ` : '';
        
        // Create preview HTML
        const previewHTML = `
            <div id="pathway-preview" style="margin-top: 10px; padding: 15px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;">
                <h4 style="margin: 0 0 8px 0; color: #29235C;">Pathway Details:</h4>
                <p style="margin: 0 0 8px 0;"><strong>Title:</strong> ${title}</p>
                ${description ? `<div style="margin-bottom: 10px;"><strong>Description:</strong><br/>${descriptionHTML}</div>` : '<p style="margin: 0 0 10px 0; color: #666; font-style: italic;">No description available</p>'}
                ${figureHTML}
            </div>
        `;
        
        // Insert after pathway dropdown
        $("#wp_id").parent().after(previewHTML);
    }

    hidePathwayPreview() {
        $("#pathway-preview").remove();
    }

    loadDataVersions() {
        // Only load version info if we're on a page that has the version info element
        if ($("#version-info").length === 0) {
            return;
        }
        
        $.getJSON("/get_data_versions")
            .done((data) => {
                // Version data loaded successfully
                this.displayVersionInfo(data);
            })
            .fail((xhr, status, error) => {
                console.warn("Failed to load version information:", error);
                $("#version-info").html('<span style="color: #999;">Version information unavailable</span>');
            });
    }

    displayVersionInfo(versions) {
        let versionHtml = '';
        
        if (versions.aop_wiki) {
            versionHtml += `
                <div style="margin-bottom: 3px;">
                    <strong>AOP-Wiki:</strong> ${versions.aop_wiki.version}
                    ${versions.aop_wiki.date !== 'Unknown' ? ` (${versions.aop_wiki.date})` : ''}
                </div>
            `;
        }
        
        if (versions.wikipathways) {
            versionHtml += `
                <div style="margin-bottom: 3px;">
                    <strong>WikiPathways:</strong> ${versions.wikipathways.version}
                    ${versions.wikipathways.date !== 'Unknown' ? ` (${versions.wikipathways.date})` : ''}
                </div>
            `;
        }
        
        if (versionHtml) {
            $("#version-info").html(versionHtml);
        } else {
            $("#version-info").html('<span style="color: #999;">Version information not available</span>');
        }
    }

    populatePathwayDropdowns() {
        // Populate all existing pathway dropdowns while preserving current selections
        $("select[name='wp_id']").each((index, dropdown) => {
            const $dropdown = $(dropdown);
            const currentValue = $dropdown.val(); // Store current selection
            
            $dropdown.empty();
            $dropdown.append('<option value="" disabled selected>Select a Pathway</option>');
            
            this.pathwayOptions.forEach(option => {
                const svgUrl = `https://www.wikipathways.org/wikipathways-assets/pathways/${option.pathwayID}/${option.pathwayID}.svg`;
                $dropdown.append(
                    `<option value="${option.pathwayID}" 
                     data-title="${option.pathwayTitle}"
                     data-description="${option.pathwayDescription || ''}"
                     data-svg-url="${svgUrl}">${option.pathwayID} - ${option.pathwayTitle}</option>`
                );
            });
            
            // Restore the previous selection if it existed
            if (currentValue && currentValue !== '') {
                $dropdown.val(currentValue);
            }
        });
    }

    addPathwaySelection() {
        const $selections = $("#pathway-selections");
        const currentCount = $selections.find(".pathway-selection-group").length;
        
        // Limit to maximum 2 pathways
        if (currentCount >= 2) {
            this.showMessage("Maximum of 2 pathways allowed for optimal assessment workflow.", "warning");
            return;
        }
        
        // Create new pathway selection group
        const newIndex = currentCount;
        const $newGroup = $(`
            <div class="pathway-selection-group" data-index="${newIndex}" style="flex: 1; min-width: 300px; max-width: calc(50% - 10px);">
                <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; background: #f8fafc;">
                    <div style="display: flex; gap: 10px; align-items: flex-start; margin-bottom: 15px;">
                        <select name="wp_id" required style="flex: 1;">
                            <option value="" disabled selected>Select Second Pathway</option>
                        </select>
                        <button type="button" class="remove-pathway-btn" onclick="window.KEWPApp.removePathwaySelection(${newIndex})" 
                                style="background: #dc3545; color: white; border: none; padding: 8px 12px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                            Remove
                        </button>
                    </div>
                    <div class="pathway-info" style="min-height: 100px; display: none;">
                        <!-- Pathway information will be inserted here -->
                    </div>
                </div>
            </div>
        `);
        
        $selections.append($newGroup);
        
        // Update the first pathway button text
        $selections.find(".add-pathway-btn").text("Max 2").prop("disabled", true).css("background", "#6c757d");
        
        // Populate the new dropdown with pathway options
        if (this.pathwayOptions) {
            this.populatePathwayDropdowns();
        }
        
        // Update event handlers for the new dropdown
        this.setupPathwayEventHandlers();
        
        // Update the hidden input field
        this.updateSelectedPathways();
    }

    removePathwaySelection(index) {
        const $group = $(`.pathway-selection-group[data-index="${index}"]`);
        $group.remove();
        
        // Update the hidden input field
        this.updateSelectedPathways();
        
        // Hide pathway preview if this was the displayed one
        this.hidePathwayPreview();
        
        // Check if there's only one pathway group left, and if so, revert the "Add 2nd" button
        const $selections = $("#pathway-selections");
        const remainingGroups = $selections.find(".pathway-selection-group").length;
        
        if (remainingGroups === 1) {
            // Revert the "Add 2nd" button to its original state
            $selections.find(".add-pathway-btn")
                .text("Add 2nd")
                .prop("disabled", false)
                .css("background", "#307BBF");
        }
        
        // Toggle assessment section to update based on remaining pathways
        this.toggleAssessmentSection();
    }

    updateSelectedPathways() {
        const selectedPathways = [];
        $("select[name='wp_id']").each((index, dropdown) => {
            const value = $(dropdown).val();
            if (value) {
                selectedPathways.push(value);
            }
        });
        
        // Update the hidden field with selected pathways (comma-separated)
        $("#wp_id").val(selectedPathways.join(','));
        
        // Update form validation state
        const hasSelection = selectedPathways.length > 0;
        $("select[name='wp_id']").prop('required', !hasSelection);
        if (hasSelection) {
            $("select[name='wp_id']").first().prop('required', true);
        }
        
        // Update pathway selections
    }

    setupPathwayEventHandlers() {
        // Remove existing handlers to prevent duplication
        $(document).off('change', "select[name='wp_id']");
        
        // Add pathway selection change handlers
        $(document).on('change', "select[name='wp_id']", (e) => {
            this.handlePathwaySelection(e);
            this.updateSelectedPathways();
            this.toggleAssessmentSection();
        });
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
        const selectedPathways = [];
        $("select[name='wp_id']").each((index, dropdown) => {
            const value = $(dropdown).val();
            if (value) {
                const option = $(dropdown).find('option:selected');
                selectedPathways.push({
                    id: value,
                    title: option.data('title') || value,
                    index: $(dropdown).closest('.pathway-selection-group').data('index')
                });
            }
        });
        
        // Debug logging
        console.log('toggleAssessmentSection called:', {
            keSelected: keSelected,
            selectedPathwaysCount: selectedPathways.length,
            selectedPathways: selectedPathways
        });
        
        if (keSelected && selectedPathways.length > 0) {
            // Show the confidence guide section
            $("#confidence-guide").show();
            
            // Show loading state in the pathway assessments area
            $("#pathway-assessments").html(`
                <div style="text-align: center; padding: 20px;">
                    <div style="margin-bottom: 10px; color: #666;">Generating confidence assessments...</div>
                    <div style="display: inline-block; width: 20px; height: 20px; border: 2px solid #f3f3f3; border-top: 2px solid #307BBF; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                </div>
            `);
            
            // Hide assessment completion section while loading
            $("#assessment-completion").hide();
            
            // Delay to show loading state, then generate assessments
            setTimeout(() => {
                this.generatePathwayAssessments(selectedPathways);
                // Pre-fill biological level if available
                this.preFillBiologicalLevel();
            }, 300);
        } else {
            $("#confidence-guide").hide();
            this.resetGuide();
        }
    }

    generatePathwayAssessments(selectedPathways) {
        console.log('generatePathwayAssessments called with:', selectedPathways);
        
        const $assessments = $("#pathway-assessments");
        $assessments.empty();
        
        selectedPathways.forEach((pathway, index) => {
            console.log(`Creating assessment ${index} for pathway:`, pathway);
            const assessmentHTML = this.createPathwayAssessment(pathway, index);
            $assessments.append(assessmentHTML);
        });
        
        // Show completion button if assessments exist
        if (selectedPathways.length > 0) {
            $("#assessment-completion").show();
        } else {
            $("#assessment-completion").hide();
        }
        
        // Update assessment status
        this.updateAssessmentStatus();
    }

    createPathwayAssessment(pathway, index) {
        const assessmentId = `assessment-${pathway.index}`;
        
        return `
            <div class="pathway-assessment pathway-assessment-container" data-pathway-id="${pathway.id}" data-pathway-index="${pathway.index}">
                
                <h3 style="margin: 0 0 15px 0; color: #29235C; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">
                    Assessment for: ${pathway.title}
                    <span style="font-size: 14px; color: #666; font-weight: normal;">(${pathway.id})</span>
                </h3>
                
                <div class="assessment-steps" data-assessment-id="${assessmentId}">
                    <div class="assessment-step" data-step="step1">
                        <h4>1. What is the relationship between the pathway and Key Event?
                            <span class="tooltip" data-tooltip="• Causative: The pathway directly causes or leads to the Key Event
• Responsive: The Key Event triggers or activates the pathway
• Bidirectional: Both causative and responsive relationships exist
• Unclear: The relationship exists but directionality is uncertain">❓</span>
                        </h4>
                        <div class="btn-group" data-step="step1" data-assessment="${assessmentId}">
                            <button class="btn-option" data-value="causative">Causative</button>
                            <button class="btn-option" data-value="responsive">Responsive</button>
                            <button class="btn-option" data-value="bidirectional">Bidirectional</button>
                            <button class="btn-option" data-value="unclear">Unclear</button>
                        </div>
                    </div>

                    <div class="assessment-step" data-step="step2" style="display: none;">
                        <h4>2. What is the basis for this mapping?
                            <span class="tooltip" data-tooltip="Base your answer on your existing knowledge:
• Known: You've seen this documented in literature or databases
• Likely: Strong biological reasoning supports this connection
• Possible: Plausible hypothesis that makes biological sense
• Uncertain: Speculative or requires investigation

You don't need to search papers - answer based on what you already know.">❓</span>
                        </h4>
                        <div class="btn-group" data-step="step2" data-assessment="${assessmentId}">
                            <button class="btn-option" data-value="known">Known connection</button>
                            <button class="btn-option" data-value="likely">Likely connection</button>
                            <button class="btn-option" data-value="possible">Possible connection</button>
                            <button class="btn-option" data-value="uncertain">Uncertain connection</button>
                        </div>
                    </div>

                    <div class="assessment-step" data-step="step3" style="display: none;">
                        <h4>3. How specific is the pathway to this Key Event?
                            <span class="tooltip" data-tooltip="Consider pathway scope:
• KE-specific: The pathway is specifically about this Key Event
• Includes KE: The pathway covers this KE plus other related processes
• Loosely related: The pathway is very broad or the connection is indirect

This helps identify which pathways need to be more specific.">❓</span>
                        </h4>
                        <div class="btn-group" data-step="step3" data-assessment="${assessmentId}">
                            <button class="btn-option" data-value="specific">KE-specific</button>
                            <button class="btn-option" data-value="includes">Includes KE</button>
                            <button class="btn-option" data-value="loose">Loosely related</button>
                        </div>
                    </div>

                    <div class="assessment-step" data-step="step4" style="display: none;">
                        <h4>4. How much of the KE mechanism is captured by the pathway?
                            <span class="tooltip" data-tooltip="Evaluate pathway completeness:
• Complete: All major biological steps/aspects of the KE are in the pathway
• Key steps: The pathway covers important parts but is missing some aspects
• Minor aspects: Only a small portion of the KE mechanism is represented

This helps identify gaps in existing pathways for future development.">❓</span>
                        </h4>
                        <div class="btn-group" data-step="step4" data-assessment="${assessmentId}">
                            <button class="btn-option" data-value="complete">Complete mechanism</button>
                            <button class="btn-option" data-value="keysteps">Key steps only</button>
                            <button class="btn-option" data-value="minor">Minor aspects</button>
                        </div>
                    </div>
                </div>
                
                <div class="assessment-result">
                    <p><strong>Result:</strong> <span class="confidence-result">—</span></p>
                    <p><strong>Connection:</strong> <span class="connection-result">—</span></p>
                    <p class="score-details" style="font-size: 12px; color: #666; margin: 5px 0 0 0;">—</p>
                </div>
            </div>
        `;
    }

    updateAssessmentStatus() {
        const totalAssessments = $('.pathway-assessment').length;
        const completedAssessments = $('.pathway-assessment .assessment-result:visible').length;
        
        const statusText = `${completedAssessments}/${totalAssessments} assessments completed`;
        $('#assessment-status').text(statusText);
        
        if (completedAssessments === totalAssessments && totalAssessments > 0) {
            $('#complete-all-assessments').text('Proceed to Submission').css('background', '#28a745');
        } else {
            $('#complete-all-assessments').text('Complete All Assessments').css('background', '#6c757d');
        }
    }

    handleCompleteAllAssessments() {
        const totalAssessments = $('.pathway-assessment').length;
        const completedAssessments = $('.pathway-assessment .assessment-result:visible').length;
        
        if (completedAssessments !== totalAssessments) {
            this.showMessage("Please complete all pathway assessments before proceeding.", "warning");
            return;
        }
        
        // Show Step 4 results instead of jumping to confirmation
        this.populateStep4Results();
        this.showStep4();
    }

    populateStep4Results() {
        const selectedPathways = [];
        $("select[name='wp_id']").each((index, dropdown) => {
            const value = $(dropdown).val();
            if (value) {
                const option = $(dropdown).find('option:selected');
                selectedPathways.push({
                    id: value,
                    title: option.data('title') || value,
                    index: $(dropdown).closest('.pathway-selection-group').data('index')
                });
            }
        });

        console.log('populateStep4Results debug:', {
            selectedPathways: selectedPathways,
            pathwayResults: this.pathwayResults,
            pathwayAssessments: this.pathwayAssessments
        });

        if (selectedPathways.length <= 1) {
            // Single pathway - populate existing single pathway Step 4 content
            $('#single-pathway-results').show();
            $('#multi-pathway-results').hide();
            
            // Get the single pathway result
            const pathway = selectedPathways[0];
            const result = this.pathwayResults[pathway.id];
            
            console.log('Single pathway result:', {pathway, result});
            
            if (result) {
                // Update the single pathway results display
                $('#auto-confidence').text(result.confidence.charAt(0).toUpperCase() + result.confidence.slice(1));
                $('#auto-connection').text(result.connection_type.charAt(0).toUpperCase() + result.connection_type.slice(1));
                
                // Also update the hidden form fields for submission
                $('#confidence_level').val(result.confidence);
                $('#connection_type').val(result.connection_type);
                
                console.log('Updated single pathway display:', {
                    confidence: $('#auto-confidence').text(),
                    connection: $('#auto-connection').text()
                });
            }
            return;
        }
        
        // Hide single pathway results, show multi-pathway results
        $('#single-pathway-results').hide();
        $('#multi-pathway-results').show();

        // Multi-pathway Step 4 results
        let resultsHTML = `
            <div class="multi-pathway-results">
                <h3>Assessment Results Summary</h3>
                <p>Review the confidence assessments for each pathway mapping:</p>
                <div class="results-table">
        `;

        selectedPathways.forEach(pathway => {
            const result = this.pathwayResults[pathway.id];
            if (!result) return;

            const confidenceClass = result.confidence === 'high' ? 'success' : 
                                  result.confidence === 'medium' ? 'warning' : 'secondary';
            
            const connectionTypeDisplay = result.connection_type.charAt(0).toUpperCase() + result.connection_type.slice(1);
            const confidenceDisplay = result.confidence.charAt(0).toUpperCase() + result.confidence.slice(1);

            resultsHTML += `
                <div class="result-item" style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 10px 0; background: #f8fafc;">
                    <h4 style="margin: 0 0 10px 0; color: #29235C;">${pathway.title}</h4>
                    <p style="margin: 5px 0;"><strong>Pathway ID:</strong> ${pathway.id}</p>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 10px 0;">
                        <div>
                            <p style="margin: 5px 0;"><strong>Confidence Level:</strong> 
                                <span class="confidence-badge confidence-${result.confidence}" style="background: ${confidenceClass === 'success' ? '#d4edda' : confidenceClass === 'warning' ? '#fff3cd' : '#e2e3e5'}; color: ${confidenceClass === 'success' ? '#155724' : confidenceClass === 'warning' ? '#856404' : '#495057'}; padding: 2px 8px; border-radius: 3px; font-weight: bold;">
                                    ${confidenceDisplay}
                                </span>
                            </p>
                            <p style="margin: 5px 0;"><strong>Connection Type:</strong> ${connectionTypeDisplay}</p>
                        </div>
                        <div>
                            <p style="margin: 5px 0;"><strong>Assessment Score:</strong> ${result.score.toFixed(1)}</p>
                            <p style="margin: 5px 0; font-size: 0.9em; color: #666;"><strong>Basis:</strong> ${result.evidence || 'Multi-factor assessment'}</p>
                        </div>
                    </div>
                </div>
            `;
        });

        resultsHTML += `
                </div>
                <div style="margin-top: 20px; padding: 15px; background: #e7f3ff; border-radius: 6px; border-left: 4px solid #307BBF;">
                    <p style="margin: 0; font-weight: bold; color: #29235C;">Ready to Submit</p>
                    <p style="margin: 5px 0 0 0; color: #555;">All assessments completed. Review the results above and proceed to Step 5 to submit your mappings.</p>
                </div>
            </div>
        `;

        // Update Step 4 content
        $('#step-3-result').html(`
            <h2>Step 4: Assessment Results</h2>
            ${resultsHTML}
        `);

        // Store results for form submission
        this.multiPathwayResults = selectedPathways.map(pathway => ({
            ...pathway,
            ...this.pathwayResults[pathway.id]
        }));
    }

    showStep4() {
        console.log('showStep4 called');
        
        // Show Step 4 section
        $('#step-3-result').show();
        
        console.log('Step 4 elements visibility:', {
            'step-3-result_visible': $('#step-3-result').is(':visible'),
            'single-pathway-results_exists': $('#single-pathway-results').length,
            'multi-pathway-results_exists': $('#multi-pathway-results').length
        });
        
        // Scroll to Step 4
        $('html, body').animate({
            scrollTop: $('#step-3-result').offset().top - 20
        }, 500);
        
        // Enable Step 5 (submission section)
        $('#step-5-submit').show();
        $('#mapping-form button[type="submit"]').prop('disabled', false).text('Review & Submit Mappings');
        
        this.showMessage("Assessment completed! Review your results in Step 4 and proceed to Step 5.", "success");
    }

    // Map UI connection types to server-accepted values
    mapConnectionTypeForServer(uiConnectionType) {
        const mapping = {
            'causative': 'causative',
            'responsive': 'responsive', 
            'bidirectional': 'other',
            'unclear': 'undefined'
        };
        return mapping[uiConnectionType] || 'undefined';
    }

    async handleMultiPathwaySubmission() {
        this.showMessage("Checking for duplicate mappings...", "info");
        
        const keId = $("#ke_id").val();
        const keTitle = $("#ke_id option:selected").data("title");
        
        const checkResults = [];
        let hasExactDuplicates = false;
        
        // Check each pathway for duplicates
        for (const pathway of this.multiPathwayResults) {
            const checkData = {
                ke_id: keId,
                ke_title: keTitle,
                wp_id: pathway.id,
                wp_title: pathway.title,
                connection_type: this.mapConnectionTypeForServer(pathway.connection_type),
                confidence_level: pathway.confidence,
                csrf_token: this.csrfToken
            };
            
            try {
                const response = await $.post("/check", checkData);
                checkResults.push({
                    pathway: pathway,
                    checkResult: response,
                    formData: checkData
                });
                
                if (response.pair_exists) {
                    hasExactDuplicates = true;
                }
            } catch (error) {
                console.error('Error checking pathway:', pathway.id, error);
                this.showMessage("Error checking for duplicates. Please try again.", "error");
                return;
            }
        }
        
        // If any exact duplicates found, show error and stop
        if (hasExactDuplicates) {
            const duplicatePathways = checkResults
                .filter(r => r.checkResult.pair_exists)
                .map(r => r.pathway.title)
                .join(', ');
            this.showMessage(`Duplicate mappings found for: ${duplicatePathways}. Please remove these pathways or modify their assessment.`, "error");
            return;
        }
        
        // Show comprehensive preview with all mappings and existing entries
        this.showMultiPathwayPreview(checkResults);
    }

    showMultiPathwayPreview(checkResults) {
        const keId = $("#ke_id").val();
        const keTitle = $("#ke_id option:selected").data("title");
        const keDescription = $("#ke_id option:selected").data('description') || '';
        const biolevel = $("#ke_id option:selected").data('biolevel') || '';
        
        // Get user information
        const isLoggedIn = $("body").data("is-logged-in") === true;
        let userInfo = 'Anonymous';
        if (isLoggedIn) {
            const welcomeText = $('header nav p').text();
            const usernameMatch = welcomeText.match(/Welcome,\s*([^(]+)/);
            if (usernameMatch) {
                userInfo = `GitHub: ${usernameMatch[1].trim()}`;
            }
        }
        
        let previewHTML = `
            <div class="existing-entries-container">
                <h3>Multi-Pathway Mapping Preview & Confirmation</h3>
                <p>Please carefully review all your pathway mappings before submitting:</p>
                
                <div class="ke-info-section" style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 15px 0;">
                    <h4 style="color: #29235C; margin-top: 0;">🧬 Key Event Information</h4>
                    <p><strong>KE ID:</strong> ${keId}</p>
                    <p><strong>KE Title:</strong> ${keTitle}</p>
                    <p><strong>Biological Level:</strong> <span style="background-color: #e3f2fd; padding: 2px 6px; border-radius: 3px;">${biolevel || 'Not specified'}</span></p>
                    <div><strong>Description:</strong><br/>${this.createCollapsibleDescription(keDescription, 'preview-ke-desc')}</div>
                </div>
                
                <h4>New Mappings to be Added (${checkResults.length})</h4>
        `;
        
        // Show each new mapping
        checkResults.forEach((result, index) => {
            const pathway = result.pathway;
            const confidenceClass = pathway.confidence === 'high' ? '#d4edda' : 
                                  pathway.confidence === 'medium' ? '#fff3cd' : '#f8d7da';
            const confidenceColor = pathway.confidence === 'high' ? '#155724' : 
                                  pathway.confidence === 'medium' ? '#856404' : '#721c24';
            
            previewHTML += `
                <div class="new-mapping-item" style="border: 2px solid #307BBF; background: #f0f8ff; padding: 15px; margin: 10px 0; border-radius: 6px;">
                    <h5 style="color: #29235C; margin-top: 0;">Mapping ${index + 1}: ${pathway.title}</h5>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div>
                            <p><strong>Pathway ID:</strong> ${pathway.id}</p>
                            <p><strong>Connection Type:</strong> ${pathway.connection_type.charAt(0).toUpperCase() + pathway.connection_type.slice(1)}</p>
                        </div>
                        <div>
                            <p><strong>Confidence Level:</strong> 
                                <span style="background: ${confidenceClass}; color: ${confidenceColor}; padding: 2px 8px; border-radius: 3px; font-weight: bold;">
                                    ${pathway.confidence.charAt(0).toUpperCase() + pathway.confidence.slice(1)}
                                </span>
                            </p>
                            <p><strong>Assessment Score:</strong> ${pathway.score.toFixed(1)}</p>
                        </div>
                    </div>
                    <p><strong>User:</strong> ${userInfo}</p>
                </div>
            `;
        });
        
        // Show existing entries if any
        const hasExistingEntries = checkResults.some(r => r.checkResult.ke_exists);
        if (hasExistingEntries) {
            previewHTML += `<h4>Existing Mappings for this Key Event</h4>`;
            
            checkResults.forEach(result => {
                if (result.checkResult.ke_exists && result.checkResult.existing_entries) {
                    result.checkResult.existing_entries.forEach(entry => {
                        previewHTML += `
                            <div class="existing-mapping-item" style="border: 1px solid #dee2e6; background: #f8f9fa; padding: 12px; margin: 8px 0; border-radius: 4px;">
                                <p><strong>Existing:</strong> ${entry.ke_id} → ${entry.wp_id} (${entry.wp_title})</p>
                                <p><strong>Confidence:</strong> ${entry.confidence_level} | <strong>Connection:</strong> ${entry.connection_type}</p>
                                <p><strong>Added by:</strong> ${entry.created_by || 'Unknown'}</p>
                            </div>
                        `;
                    });
                }
            });
        }
        
        previewHTML += `
                <div class="confirmation-section" style="margin-top: 25px; padding: 20px; background: #fff3cd; border-radius: 6px;">
                    <p class="confirmation-title" style="font-weight: bold; margin-bottom: 10px;">Ready to Submit ${checkResults.length} New Mappings?</p>
                    <p class="confirmation-subtitle">These mappings will be added to the database and made available for other researchers.</p>
                    <div style="text-align: center; margin-top: 15px;">
                        <button id="confirm-multi-final-submit" style="background: #28a745; color: white; border: none; padding: 15px 30px; border-radius: 6px; margin-right: 10px; cursor: pointer; font-weight: bold;">
                            Yes, Submit All ${checkResults.length} Mappings
                        </button>
                        <button id="cancel-multi-final-submit" style="background: #6c757d; color: white; border: none; padding: 15px 30px; border-radius: 6px; cursor: pointer;">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        $("#existing-entries").html(previewHTML);
        
        // Scroll to preview
        $('html, body').animate({
            scrollTop: $("#existing-entries").offset().top - 20
        }, 500);
        
        // Handle confirmation buttons
        $("#confirm-multi-final-submit").on('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            this.submitMultiplePathwayMappings(checkResults);
        });

        $("#cancel-multi-final-submit").on('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            $("#existing-entries").html("");
        });
    }

    async submitMultiplePathwayMappings(checkResults) {
        // Check authentication
        if (!this.isLoggedIn) {
            this.showMessage("Please log in with GitHub to submit mappings.", "error");
            setTimeout(() => {
                this.saveFormState();
                window.location.href = '/auth/login';
            }, 2000);
            return;
        }
        
        this.showMessage("Submitting your mappings...", "info");
        
        let successCount = 0;
        let failureCount = 0;
        const errors = [];
        
        for (const result of checkResults) {
            try {
                console.log(`Submitting mapping for ${result.pathway.title} with data:`, result.formData);
                const response = await $.post("/submit", result.formData);
                successCount++;
                console.log(`Successfully submitted mapping for ${result.pathway.title}:`, response);
            } catch (xhr) {
                failureCount++;
                console.error(`Failed to submit mapping for ${result.pathway.title}:`, xhr);
                console.error('Response status:', xhr.status);
                console.error('Response text:', xhr.responseText);
                console.error('Form data that failed:', result.formData);
                
                let errorMsg = `${result.pathway.title}: `;
                if (xhr.responseJSON?.error) {
                    errorMsg += xhr.responseJSON.error;
                } else if (xhr.status === 401 || xhr.status === 403) {
                    errorMsg += 'Authentication required';
                } else if (xhr.status === 400) {
                    errorMsg += 'Invalid data';
                } else {
                    errorMsg += `Server error (${xhr.status})`;
                }
                errors.push(errorMsg);
            }
        }
        
        // Show results
        if (successCount === checkResults.length) {
            this.showMessage(`Successfully submitted all ${successCount} mappings!`, "success");
            $("#existing-entries").html("");
            this.resetForm();
        } else if (successCount > 0) {
            const errorDetails = errors.join('\n• ');
            this.showMessage(`Submitted ${successCount} of ${checkResults.length} mappings successfully.\n\nFailed submissions:\n• ${errorDetails}\n\nPlease check the browser console for detailed error information.`, "warning");
            console.error('Detailed submission errors:', errors);
        } else {
            const errorDetails = errors.join('\n• ');
            this.showMessage(`All submissions failed:\n• ${errorDetails}\n\nPlease check the browser console for detailed error information.`, "error");
            console.error('All submission errors:', errors);
        }
    }

    showMultiPathwayConfirmation() {
        const keTitle = $("#ke_id option:selected").text();
        const keId = $("#ke_id").val();
        
        let confirmationHTML = `
            <div class="confirmation-dialog" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;">
                <div style="background: white; border-radius: 8px; padding: 30px; max-width: 800px; max-height: 80vh; overflow-y: auto;">
                    <h2 style="margin-top: 0; color: #29235C;">Confirm Multiple Pathway Mappings</h2>
                    <p><strong>Key Event:</strong> ${keTitle}</p>
                    <div style="margin: 20px 0;">
        `;
        
        // Add each pathway mapping summary
        $('.pathway-assessment').each((index, element) => {
            const $assessment = $(element);
            const pathwayId = $assessment.data('pathway-id');
            const pathwayTitle = this.pathwayOptions.find(p => p.pathwayID === pathwayId)?.pathwayTitle || pathwayId;
            const result = this.pathwayResults[pathwayId];
            
            if (!result || result.skipped) {
                confirmationHTML += `
                    <div style="border: 1px solid #f8d7da; background: #f8d7da; padding: 15px; margin: 10px 0; border-radius: 4px;">
                        <h4 style="margin: 0 0 8px 0; color: #721c24;">${pathwayTitle} (${pathwayId})</h4>
                        <p style="margin: 0; color: #721c24;"><strong>Status:</strong> Skipped (not biologically relevant)</p>
                    </div>
                `;
            } else {
                confirmationHTML += `
                    <div class="suggestion-panel-container">
                        <h4 style="margin: 0 0 8px 0; color: #29235C;">${pathwayTitle} (${pathwayId})</h4>
                        <p style="margin: 5px 0;"><strong>Confidence:</strong> ${result.confidence}</p>
                        <p style="margin: 5px 0;"><strong>Connection Type:</strong> ${result.connection_type}</p>
                        <p style="margin: 5px 0;"><strong>Score:</strong> ${result.score.toFixed(1)}</p>
                    </div>
                `;
            }
        });
        
        confirmationHTML += `
                    </div>
                    <div style="text-align: center; margin-top: 25px;">
                        <button id="confirm-multi-submit" style="background: #28a745; color: white; border: none; padding: 15px 30px; border-radius: 6px; margin-right: 10px; cursor: pointer;">
                            Submit All Mappings
                        </button>
                        <button id="cancel-multi-submit" style="background: #6c757d; color: white; border: none; padding: 15px 30px; border-radius: 6px; cursor: pointer;">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(confirmationHTML);
        
        // Add event handlers
        $('#confirm-multi-submit').on('click', () => {
            $('.confirmation-dialog').remove();
            // Note: This old popup workflow has been replaced with the new Step 4 → Step 5 workflow
            this.showMessage("Please use the new Step 4 → Step 5 workflow instead.", "info");
        });
        
        $('#cancel-multi-submit').on('click', () => {
            $('.confirmation-dialog').remove();
        });
    }

    // Old submitMultiplePathwayMappings function removed - replaced with new workflow

    // Old submitIndividualMappings function removed - replaced with new workflow

    resetGuide() {
        const sections = ["#step2", "#step3", "#step4", "#step5"];
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
        // Biological level is now automatically considered in the confidence scoring
        // No need to pre-fill UI elements, but we store it for use in evaluateConfidence
        if (this.selectedBiolevel) {
            // Biological level detected for confidence scoring
        }
    }

    resetForm() {
        $("#ke_id").val("").trigger('change');
        
        // Reset pathway selections - remove all but first dropdown
        const $selections = $("#pathway-selections");
        $selections.find(".pathway-selection-group").not(':first').remove();
        
        // Reset the first pathway dropdown and button
        $("select[name='wp_id']").val("").trigger('change');
        $selections.find(".add-pathway-btn").text("Add 2nd").prop("disabled", false).css("background", "#307BBF");
        $selections.find(".pathway-info").hide();
        $("#wp_id").val("");
        
        // Reset assessment data
        this.pathwayAssessments = {};
        this.pathwayResults = {};
        $("#pathway-assessments").empty();
        $("#assessment-completion").hide();
        
        // Reset Step 4 and Step 5
        $("#step-3-result").hide();
        $("#step-5-submit").hide();
        $("#mapping-form button[type='submit']").prop('disabled', true).text('Complete Assessment First');
        
        // Clear existing entries
        $("#existing-entries").html("");
        
        // Clear multi-pathway state
        this.multiPathwayResults = null;
        
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
        // Populate submission summary
        const summaryHtml = `
            <div style="margin-bottom: 15px;">
                <div style="margin-bottom: 10px;">
                    <strong style="color: #29235C;">Key Event:</strong><br>
                    <span style="font-family: monospace; font-size: 13px; color: #666;">${formData.ke_id}</span><br>
                    <span style="font-size: 14px;">${formData.ke_title}</span>
                </div>
                <div style="text-align: center; margin: 10px 0; color: #307BBF; font-size: 20px;">↓</div>
                <div style="margin-bottom: 10px;">
                    <strong style="color: #29235C;">WikiPathway:</strong><br>
                    <span style="font-family: monospace; font-size: 13px; color: #666;">${formData.wp_id}</span><br>
                    <span style="font-size: 14px;">${formData.wp_title}</span>
                </div>
            </div>
            <div style="border-top: 1px solid #e2e8f0; padding-top: 15px; display: flex; justify-content: space-around; font-size: 14px;">
                <div>
                    <strong style="color: #29235C;">Connection:</strong><br>
                    <span style="color: #666;">${formData.connection_type.charAt(0).toUpperCase() + formData.connection_type.slice(1)}</span>
                </div>
                <div>
                    <strong style="color: #29235C;">Confidence:</strong><br>
                    <span style="color: #666;">${formData.confidence_level.charAt(0).toUpperCase() + formData.confidence_level.slice(1)}</span>
                </div>
            </div>
        `;

        $("#submissionSummary").html(summaryHtml);

        // Display the modal
        const modal = $("#thankYouModal");
        modal.css("display", "flex");

        // Close modal handlers
        $("#closeThankYouModal").off("click").on("click", () => {
            modal.hide();
        });

        // Close on background click
        modal.off("click").on("click", (e) => {
            if (e.target.id === "thankYouModal") {
                modal.hide();
            }
        });

        // Auto-close modal after 10 seconds
        setTimeout(() => {
            modal.fadeOut();
        }, 10000);
    }

    loadPathwaySuggestions(keId, keTitle) {
        // Loading pathway suggestions
        
        // Show loading indicator
        this.showPathwaySuggestionsLoading();
        
        // Encode parameters for URL
        const encodedKeId = encodeURIComponent(keId);
        const encodedKeTitle = encodeURIComponent(keTitle);
        const encodedBioLevel = encodeURIComponent(this.selectedBiolevel || '');
        
        // Make AJAX request for suggestions with biological level context
        $.getJSON(`/suggest_pathways/${encodedKeId}?ke_title=${encodedKeTitle}&bio_level=${encodedBioLevel}&limit=8`)
            .done((data) => {
                // Pathway suggestions loaded successfully
                this.displayPathwaySuggestions(data);
            })
            .fail((xhr, status, error) => {
                console.error('Failed to load pathway suggestions:', error);
                this.showPathwaySuggestionsError('Unable to load pathway suggestions. You can still browse pathways manually using the dropdown below.');
            });
    }

    showPathwaySuggestionsLoading() {
        // Remove existing suggestions
        $("#pathway-suggestions").remove();
        
        const loadingHtml = `
            <div id="pathway-suggestions" style="margin-top: 15px; padding: 15px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color: #29235C;">Suggested Pathways</h3>
                <div style="display: flex; align-items: center; color: #666;">
                    <div style="margin-right: 10px; font-size: 12px;">Loading...</div>
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
                <h3 style="margin: 0 0 15px 0; color: #29235C;">Suggested Pathways for Selected KE</h3>
        `;

        // Show gene information if available
        if (data.genes_found > 0) {
            suggestionsHtml += `
                <div style="margin-bottom: 15px; padding: 10px; background-color: #e3f2fd; border-radius: 4px; font-size: 14px;">
                    <strong>Associated Genes:</strong> ${data.gene_list.join(', ')} (${data.genes_found} gene${data.genes_found !== 1 ? 's' : ''} found)
                </div>
            `;
        }

        // Gene-based suggestions
        if (data.gene_based_suggestions && data.gene_based_suggestions.length > 0) {
            suggestionsHtml += `
                <div class="suggestion-section" style="margin-bottom: 15px;">
                    <h4 style="margin: 0 0 10px 0; color: #307BBF;">Gene-Based Matches</h4>
                    <div class="suggestion-list">
            `;
            
            data.gene_based_suggestions.forEach(suggestion => {
                const geneOverlap = `${suggestion.matching_gene_count}/${data.genes_found} KE genes`;
                const pathwaySize = suggestion.pathway_total_genes
                    ? ` (${suggestion.matching_gene_count}/${suggestion.pathway_total_genes} pathway genes)`
                    : '';
                const displayText = geneOverlap + pathwaySize;
                const confidenceBar = this.createConfidenceBar(suggestion.confidence_score);

                suggestionsHtml += `
                    <div class="suggestion-item" style="margin-bottom: 15px; padding: 12px; background-color: #ffffff; border: 1px solid #d4edda; border-radius: 6px; cursor: pointer; transition: all 0.2s ease;"
                         onclick="window.KEWPApp.selectSuggestedPathway('${suggestion.pathwayID}', '${suggestion.pathwayTitle.replace(/'/g, "\\'")}')">
                        <div style="display: flex; gap: 12px; align-items: flex-start;">
                            <div style="flex: 1;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <strong style="color: #155724; font-size: 14px;">${suggestion.pathwayTitle}</strong>
                                    <div class="center-text">
                                        ${confidenceBar}
                                        <div style="font-size: 10px; color: #666;">Confidence</div>
                                    </div>
                                </div>
                                <div style="font-size: 12px; color: #666; margin-bottom: 4px;">
                                    ID: ${suggestion.pathwayID} | Overlap: ${displayText} (${Math.round(suggestion.gene_overlap_ratio * 100)}%)
                                </div>
                                <div style="font-size: 11px; color: #666; margin-bottom: 8px;">
                                    Matching genes: ${suggestion.matching_genes.join(', ')}
                                </div>
                                <button onclick="event.stopPropagation(); window.KEWPApp.showPathwayPreview('${suggestion.pathwayID}', '${suggestion.pathwayTitle.replace(/'/g, "\\'")}', '${suggestion.pathwaySvgUrl || ''}')" 
                                        style="font-size: 11px; padding: 4px 8px; background: #e3f2fd; border: 1px solid #307BBF; border-radius: 3px; color: #307BBF; cursor: pointer;">
                                    Preview Pathway
                                </button>
                            </div>
                            <div class="pathway-thumbnail" onclick="event.stopPropagation(); window.KEWPApp.showPathwayPreview('${suggestion.pathwayID}', '${suggestion.pathwayTitle.replace(/'/g, "\\'")}', '${suggestion.pathwaySvgUrl || ''}')">
                                <img src="${suggestion.pathwaySvgUrl || ''}" 
                                     style="max-width: 100%; max-height: 100%; object-fit: contain; transition: transform 0.2s ease;" 
                                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block'"
                                     onmouseover="this.style.transform='scale(1.05)'"
                                     onmouseout="this.style.transform='scale(1)'"
                                     alt="Pathway thumbnail">
                                <div style="display: none; font-size: 12px; padding: 10px;" class="text-muted center-text">No image</div>
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
                    <h4 style="margin: 0 0 10px 0; color: #307BBF;">Text-Based Matches</h4>
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
                                    <div class="center-text">
                                        ${confidenceBar}
                                        <div style="font-size: 10px; color: #666;">Confidence</div>
                                    </div>
                                </div>
                                <div style="font-size: 12px; color: #666; margin-bottom: 8px;">
                                    Pathway ID: ${suggestion.pathwayID}
                                </div>
                                <button onclick="event.stopPropagation(); window.KEWPApp.showPathwayPreview('${suggestion.pathwayID}', '${suggestion.pathwayTitle.replace(/'/g, "\\'")}', '${suggestion.pathwaySvgUrl || ''}')" 
                                        style="font-size: 11px; padding: 4px 8px; background: #e3f2fd; border: 1px solid #307BBF; border-radius: 3px; color: #307BBF; cursor: pointer;">
                                    Preview Pathway
                                </button>
                            </div>
                            <div class="pathway-thumbnail" onclick="event.stopPropagation(); window.KEWPApp.showPathwayPreview('${suggestion.pathwayID}', '${suggestion.pathwayTitle.replace(/'/g, "\\'")}', '${suggestion.pathwaySvgUrl || ''}')">
                                <img src="${suggestion.pathwaySvgUrl || ''}" 
                                     style="max-width: 100%; max-height: 100%; object-fit: contain; transition: transform 0.2s ease;" 
                                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block'"
                                     onmouseover="this.style.transform='scale(1.05)'"
                                     onmouseout="this.style.transform='scale(1)'"
                                     alt="Pathway thumbnail">
                                <div style="display: none; font-size: 12px; padding: 10px;" class="text-muted center-text">No image</div>
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
            details = "No associated genes were found in the AOP-Wiki data. Try searching manually using the dropdown below.";
        } else if (data && data.genes_found > 0) {
            details = `Found ${data.genes_found} associated gene${data.genes_found !== 1 ? 's' : ''} (${data.gene_list.join(', ')}) but no matching pathways were identified.`;
        }

        const noSuggestionsHtml = `
            <div id="pathway-suggestions" style="margin-top: 15px; padding: 15px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 5px;">
                <h3 style="margin: 0 0 10px 0; color: #29235C;">Pathway Suggestions</h3>
                <div style="color: #666; text-align: center; padding: 20px;">
                    <div style="margin-bottom: 8px; font-weight: bold;">${message}</div>
                    ${details ? `<div style="font-size: 12px; color: #888; margin-bottom: 15px;">${details}</div>` : ''}
                    <div style="margin-top: 15px; font-size: 12px; color: #307BBF;">
                        <em>Try using the search function below to find pathways manually</em>
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
                <h3 style="margin: 0 0 10px 0; color: #29235C;">Pathway Suggestions</h3>
                <div style="color: #dc3545; text-align: center; padding: 20px;">
                    <div style="font-size: 16px; margin-bottom: 10px; color: #666; font-weight: bold;">Warning</div>
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
        // Find an available pathway dropdown (either the first one or an empty second one)
        const $pathwayGroups = $(".pathway-selection-group");
        let $targetDropdown = null;
        let targetGroupIndex = null;
        
        // First, try to find an empty dropdown
        $pathwayGroups.each(function(index) {
            const $dropdown = $(this).find("select[name='wp_id']");
            if (!$dropdown.val() || $dropdown.val() === "") {
                $targetDropdown = $dropdown;
                targetGroupIndex = index;
                return false; // Break the loop
            }
        });
        
        // If no empty dropdown found and we only have 1 pathway group, add a second one automatically
        if (!$targetDropdown && $pathwayGroups.length === 1) {
            this.addPathwaySelection();
            
            // Wait for the second pathway group to be fully created and populated
            setTimeout(() => {
                // Specifically target the second (newly created) pathway group
                const $allGroups = $(".pathway-selection-group");
                if ($allGroups.length >= 2) {
                    // Get the second pathway group (index 1)
                    const $secondGroup = $allGroups.eq(1);
                    const $secondDropdown = $secondGroup.find("select[name='wp_id']");
                    
                    // Select the pathway in the second dropdown
                    const $option = $secondDropdown.find(`option[value="${pathwayId}"]`);
                    if ($option.length > 0) {
                        $secondDropdown.val(pathwayId).trigger('change');
                        this.showMessage(`Selected suggested pathway: ${pathwayTitle}`, "success");
                        
                        // Ensure the assessment section is triggered
                        setTimeout(() => {
                            this.updateSelectedPathways();
                            this.toggleAssessmentSection();
                        }, 150);
                    } else {
                        console.warn('Pathway option not found in second dropdown:', pathwayId);
                        this.showMessage(`Selected pathway is not available in the dropdown. Please try refreshing the page.`, "warning");
                    }
                } else {
                    console.error('Second pathway group not found after creation');
                }
            }, 200); // Increased timeout to ensure proper creation and population
            return; // Exit early since we're handling the selection in the setTimeout
        }
        
        // If both dropdowns are filled and we have 2 groups, don't overwrite - show message instead
        if (!$targetDropdown && $pathwayGroups.length === 2) {
            this.showMessage(`Both pathway slots are filled. Please clear one first if you want to select a different pathway.`, "warning");
            return;
        }
        
        // If still no empty dropdown found, use the first one (replace existing selection)
        if (!$targetDropdown) {
            $targetDropdown = $pathwayGroups.first().find("select[name='wp_id']");
            targetGroupIndex = 0;
        }
        
        // Find the pathway option in the target dropdown
        const $option = $targetDropdown.find(`option[value="${pathwayId}"]`);
        
        if ($option.length > 0) {
            // Select the pathway
            $targetDropdown.val(pathwayId).trigger('change');
            
            // Show success message
            this.showMessage(`Selected suggested pathway: ${pathwayTitle}`, "success");
            
            // Ensure the assessment section is triggered with a slight delay
            setTimeout(() => {
                this.updateSelectedPathways();
                this.toggleAssessmentSection();
            }, 50);
        } else {
            console.error(`Pathway option not found in dropdown: ${pathwayId}`);
            this.showMessage(`Selected pathway is not available in the dropdown. Please try refreshing the page or selecting a different pathway.`, "warning");
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
        
        // Show enhanced loading state
        $searchResults.html(`
            <div class="search-loading">
                <div style="margin-bottom: 10px;">Searching pathways...</div>
                <div style="display: inline-block; width: 16px; height: 16px; border: 2px solid #f3f3f3; border-top: 2px solid #307BBF; border-radius: 50%; animation: spin 1s linear infinite;"></div>
            </div>
        `).show();
        
        // Make search request
        $.getJSON(`/search_pathways?q=${encodeURIComponent(query)}&threshold=0.2&limit=10`)
            .done((data) => {
                this.displaySearchResults(data.results, query);
            })
            .fail((xhr, status, error) => {
                console.error('Search failed:', error);
                $searchResults.html('<div style="padding: 10px; color: #dc3545;">Unable to search pathways. Please check your internet connection and try again.</div>');
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
                                Preview
                            </button>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <div class="center-text">
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
                                <div style="display: none; font-size: 10px; color: #999; text-align: center; padding: 5px;">No image</div>
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
        
        // Find the first available pathway dropdown (select[name='wp_id'])
        const $dropdown = $("select[name='wp_id']").first();
        const $option = $dropdown.find(`option[value="${pathwayId}"]`);
        
        if ($option.length > 0) {
            // Select the pathway
            $dropdown.val(pathwayId).trigger('change');
            // Pathway selected from search results
            this.showMessage(`Selected pathway: ${pathwayTitle}`, "success");
        } else {
            // Pathway not in dropdown - need to add it dynamically
            // Adding pathway to dropdown
            
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
                        padding: 20px; overflow: auto; flex: 1; max-height: calc(95vh - 120px);
                        display: flex; flex-direction: column; align-items: center;">
                        <div id="pathway-svg-container" style="
                            width: 100%; max-width: 1200px; text-align: center;
                            border: 1px solid #ddd; border-radius: 8px; 
                            padding: 20px; background: #fafafa; position: relative;
                            min-height: 300px; max-height: calc(95vh - 200px);
                            overflow: hidden;">
                            <div style="margin-bottom: 15px; color: #666;">Loading pathway diagram...</div>
                            <div class="loading-spinner" style="display: inline-block; font-size: 32px;">Loading...</div>
                        </div>
                        
                        <!-- Action buttons -->
                        <div style="margin-top: 20px; display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;">
                            <button id="select-pathway-btn" data-pathway-id="${pathwayID}" data-pathway-title="${pathwayTitle}" 
                                    style="
                                        padding: 8px 16px; background: #307BBF; color: white; 
                                        border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">
                                Select This Pathway
                            </button>
                            <a href="https://www.wikipathways.org/index.php/Pathway:${pathwayID}" 
                               target="_blank" 
                               style="
                                    padding: 8px 16px; background: #f8f9fa; color: #307BBF; 
                                    border: 1px solid #307BBF; border-radius: 4px; 
                                    text-decoration: none; font-size: 14px; display: inline-block;">
                                View on WikiPathways
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $("body").append(modalHtml);
        
        // Add event handler for select button (using delegation since modal is dynamic)
        $(document).on('click', '#select-pathway-btn', (e) => {
            const pathwayId = $(e.target).data('pathway-id');
            const pathwayTitle = $(e.target).data('pathway-title');
            this.selectSuggestedPathway(pathwayId, pathwayTitle);
            $("#pathway-preview-modal").remove();
        });
        
        // Load the SVG
        if (svgUrl) {
            this.loadPathwaySvg(svgUrl, pathwayID);
        } else {
            $("#pathway-svg-container").html(`
                <div style="color: #666; padding: 40px;">
                    <div style="font-size: 14px; margin-bottom: 15px; color: #666;">No diagram available</div>
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
            
            // Set container size based on image shape, but limit to available modal space
            let containerWidth = isWide ? '100%' : (isTall ? '60%' : '80%');
            let containerHeight = isTall ? '50vh' : (isWide ? '40vh' : '45vh');
            
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
                            max-width: 100%;
                            height: auto;
                            width: auto;
                            transition: transform 0.3s ease;
                            user-select: none;
                            transform-origin: 0 0;
                         "
                         draggable="false">
                </div>
                
                <div style="font-size: 11px; color: #666; margin-top: 12px; text-align: center;">
                    Source: WikiPathways.org<br>
                    Use zoom controls above or scroll wheel to zoom • Click and drag to pan
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
                            onload="/* SVG loaded */">
                        <div style="padding: 40px; text-align: center; color: #666;">
                            <div style="font-size: 16px; margin-bottom: 15px; color: #dc3545; font-weight: bold;">Error</div>
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
                
                // Update zoom reset button text and scrollable area
                $('#zoom-reset').text(`${Math.round(scale * 100)}%`);
                updateScrollableArea();
            }
        }, 100);
        
        // Helper function to update scrollable area after zoom
        const updateScrollableArea = () => {
            const img = $img[0];
            if (img && img.naturalWidth && img.naturalHeight) {
                const scaledWidth = img.naturalWidth * scale;
                const scaledHeight = img.naturalHeight * scale;
                
                // Set the image container size to match scaled image
                $img.css({
                    'width': `${scaledWidth}px`,
                    'height': `${scaledHeight}px`
                });
            }
        };
        
        // Zoom controls (using delegation since modal is dynamic)
        $(document).on('click', '#zoom-in', () => {
            scale = Math.min(scale * 1.25, 5);
            $img.css('transform', `scale(${scale})`);
            $('#zoom-reset').text(`${Math.round(scale * 100)}%`);
            updateScrollableArea();
        });
        
        $(document).on('click', '#zoom-out', () => {
            scale = Math.max(scale / 1.25, 0.1);
            $img.css('transform', `scale(${scale})`);
            $('#zoom-reset').text(`${Math.round(scale * 100)}%`);
            updateScrollableArea();
        });
        
        $(document).on('click', '#zoom-reset', () => {
            scale = 1;
            $img.css('transform', 'scale(1)');
            $('#zoom-reset').text('100%');
            updateScrollableArea();
            $viewport.scrollLeft(0).scrollTop(0);
        });
        
        $(document).on('click', '#fit-width', () => {
            const containerWidth = $viewport.width();
            const imgWidth = $img[0].naturalWidth;
            scale = containerWidth / imgWidth * 0.95;
            $img.css('transform', `scale(${scale})`);
            $('#zoom-reset').text(`${Math.round(scale * 100)}%`);
            updateScrollableArea();
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
            updateScrollableArea();
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
                
                // Calculate new scroll positions
                const newScrollLeft = $viewport.scrollLeft() - deltaX;
                const newScrollTop = $viewport.scrollTop() - deltaY;
                
                // Apply scroll changes (browser will constrain to valid bounds)
                $viewport.scrollLeft(newScrollLeft);
                $viewport.scrollTop(newScrollTop);
                
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

    saveFormState() {
        try {
            const formState = {
                // Basic selections
                keId: $("#ke_id").val(),
                keTitle: $("#ke_id option:selected").data("title"),
                keDescription: $("#ke_id option:selected").data("description"),
                keBiolevel: $("#ke_id option:selected").data("biolevel"),
                
                // Pathway selections
                pathwaySelections: [],
                
                // Assessment answers
                stepAnswers: this.stepAnswers || {},
                pathwayAssessments: this.pathwayAssessments || {},
                selectedBiolevel: this.selectedBiolevel || "",
                
                // Timestamp for cleanup
                timestamp: Date.now()
            };
            
            // Collect all pathway selections
            $(".pathway-selection-group").each(function(index) {
                const $select = $(this).find("select[name='wp_id']");
                const selectedValue = $select.val();
                if (selectedValue) {
                    const $option = $select.find("option:selected");
                    formState.pathwaySelections.push({
                        index: index,
                        pathwayId: selectedValue,
                        pathwayTitle: $option.data("title"),
                        pathwayDescription: $option.data("description"),
                        pathwaySvgUrl: $option.data("svg-url")
                    });
                }
            });
            
            // Saving form state to localStorage
            localStorage.setItem('kewp_form_state', JSON.stringify(formState));
            return true;
        } catch (error) {
            console.error("Failed to save form state:", error);
            return false;
        }
    }

    restoreFormState() {
        try {
            const savedState = localStorage.getItem('kewp_form_state');
            if (!savedState) {
                return false;
            }
            
            const formState = JSON.parse(savedState);
            
            // Check if state is too old (older than 1 hour)
            const oneHour = 60 * 60 * 1000;
            if (Date.now() - formState.timestamp > oneHour) {
                localStorage.removeItem('kewp_form_state');
                return false;
            }
            
            // Restoring form state from localStorage
            
            // Restore state after dropdown options are loaded
            const restoreAfterLoad = () => {
                // Restore KE selection
                if (formState.keId) {
                    $("#ke_id").val(formState.keId).trigger('change');
                }
                
                // Restore pathway selections
                if (formState.pathwaySelections && formState.pathwaySelections.length > 0) {
                    // Ensure we have enough pathway selection groups
                    while ($(".pathway-selection-group").length < formState.pathwaySelections.length && $(".pathway-selection-group").length < 2) {
                        this.addPathwaySelection();
                    }
                    
                    // Set each pathway selection
                    formState.pathwaySelections.forEach((selection, index) => {
                        const $group = $(`.pathway-selection-group[data-index="${selection.index}"]`);
                        if ($group.length === 0) return;
                        
                        const $select = $group.find("select[name='wp_id']");
                        if ($select.find(`option[value="${selection.pathwayId}"]`).length > 0) {
                            $select.val(selection.pathwayId).trigger('change');
                        }
                    });
                    
                    // Update selections
                    setTimeout(() => {
                        this.updateSelectedPathways();
                        this.toggleAssessmentSection();
                    }, 100);
                }
                
                // Restore assessment data
                if (formState.stepAnswers) {
                    this.stepAnswers = formState.stepAnswers;
                }
                if (formState.pathwayAssessments) {
                    this.pathwayAssessments = formState.pathwayAssessments;

                    // Restore visual state for each pathway assessment
                    Object.keys(formState.pathwayAssessments).forEach(pathwayId => {
                        const answers = formState.pathwayAssessments[pathwayId];
                        const $pathwayAssessment = $(`.pathway-assessment[data-pathway-id="${pathwayId}"]`);

                        if ($pathwayAssessment.length > 0) {
                            // Restore button states for each step
                            Object.keys(answers).forEach(stepId => {
                                const value = answers[stepId];
                                const $btn = $pathwayAssessment.find(`.btn-group[data-step="${stepId}"] .btn-option[data-value="${value}"]`);

                                if ($btn.length > 0) {
                                    // Add selected class
                                    $btn.addClass("selected");

                                    // Show subsequent steps
                                    const stepNum = parseInt(stepId.replace('step', ''));
                                    for (let i = 2; i <= 4; i++) {
                                        if (i <= stepNum + 1) {
                                            $pathwayAssessment.find(`.assessment-step[data-step="step${i}"]`).show();
                                        }
                                    }
                                }
                            });

                            // If assessment is complete, evaluate and show results
                            if (answers.step1 && answers.step2 && answers.step3 && answers.step4) {
                                setTimeout(() => {
                                    this.evaluatePathwayConfidence(pathwayId);
                                }, 200);
                            }
                        }
                    });
                }
                if (formState.selectedBiolevel) {
                    this.selectedBiolevel = formState.selectedBiolevel;
                }

                // Show assessment sections if there are answers
                if (formState.pathwayAssessments && Object.keys(formState.pathwayAssessments).length > 0) {
                    $("#confidence-guide").show();
                    $("#step-3-result").show();
                    $("#step-5-submit").show();
                }

                // Form state restored successfully
                this.showMessage("Previous selections restored after login", "success");
                
                // Clear the saved state since it's been restored
                localStorage.removeItem('kewp_form_state');
            };
            
            // Wait for dropdown options to load, then restore
            if (this.pathwayOptions) {
                // Options already loaded
                restoreAfterLoad.call(this);
            } else {
                // Wait for options to load
                const checkOptions = () => {
                    if (this.pathwayOptions) {
                        restoreAfterLoad.call(this);
                    } else {
                        setTimeout(checkOptions, 200);
                    }
                };
                setTimeout(checkOptions, 500);
            }
            
            return true;
        } catch (error) {
            console.error("Failed to restore form state:", error);
            localStorage.removeItem('kewp_form_state'); // Clean up corrupted data
            return false;
        }
    }
}

// Global function for confidence evaluation
function evaluateConfidence() {
    const app = window.KEWPApp;
    const config = app.scoringConfig;

    const s1 = app.stepAnswers["step1"]; // Relationship type (causative/responsive/bidirectional/unclear)
    const s2 = app.stepAnswers["step2"]; // Evidence quality (strong/moderate/computational/none)
    const s3 = app.stepAnswers["step3"]; // Pathway specificity (direct/partial/weak)
    const s4 = app.stepAnswers["step4"]; // Coverage comprehensiveness (complete/partial/limited)

    // Calculate base score using config
    let baseScore = 0;

    // Evidence quality scoring - use config
    baseScore += config.evidence_quality[s2] || 0;

    // Pathway specificity scoring - use config
    baseScore += config.pathway_specificity[s3] || 0;

    // Coverage comprehensiveness scoring - use config
    baseScore += config.ke_coverage[s4] || 0;

    // Add biological level modifier - use config
    const bioLevel = app.selectedBiolevel ? app.selectedBiolevel.toLowerCase() : '';
    const qualifyingLevels = config.biological_level.qualifying_levels;
    const isMolecularLevel = qualifyingLevels.some(level => bioLevel.includes(level));

    if (isMolecularLevel) {
        baseScore += config.biological_level.bonus;
    }

    // Determine confidence level based on total score - use config thresholds
    let confidence = "low";
    if (baseScore >= config.confidence_thresholds.high) {
        confidence = "high";
    } else if (baseScore >= config.confidence_thresholds.medium) {
        confidence = "medium";
    }

    // Update UI with results
    $("#auto-confidence").text(confidence.charAt(0).toUpperCase() + confidence.slice(1));
    $("#auto-connection").text(s1.charAt(0).toUpperCase() + s1.slice(1));
    $("#confidence_level").val(confidence);
    $("#connection_type").val(window.KEWPApp.mapConnectionTypeForServer(s1));
    $("#evaluateBtn").hide();

    // Show detailed result message - use config max scores
    const maxScore = isMolecularLevel ?
        config.max_scores.with_bio_bonus :
        config.max_scores.without_bio_bonus;
    const detailMessage = `Assessment completed: ${confidence} confidence (score: ${baseScore}/${maxScore})${isMolecularLevel ? ' with biological level bonus' : ''}`;
    $("#ca-result").text(detailMessage);

    app.showMessage("Confidence assessment completed successfully", "success");

    // Show Step 4 and enable Step 5 for single pathway workflow
    $("#step-3-result").show();
    $("#step-5-submit").show();
    $("#mapping-form button[type='submit']").prop('disabled', false).text('Review & Submit Mapping');

    // Scroll to Step 4
    $('html, body').animate({
        scrollTop: $('#step-3-result').offset().top - 20
    }, 500);
}

// Universal function to handle Ctrl+click for opening in new tabs
function handleCtrlClick(event, url) {
    event.preventDefault();
    if (event.ctrlKey || event.metaKey) { // Ctrl (Windows/Linux) or Cmd (Mac)
        window.open(url, '_blank');
    } else {
        window.location.href = url;
    }
}

// Initialize app when document is ready
$(document).ready(() => {
    window.KEWPApp = new KEWPApp();
});