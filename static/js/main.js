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
        $("#mapping-form").on('submit', (e) => this.handleFormSubmission(e));

        // Confidence assessment handlers
        $(".btn-group").on("click", ".btn-option", (e) => this.handleConfidenceAssessment(e));

        // Dropdown change handlers
        $("#ke_id, #wp_id").on('change', () => this.toggleAssessmentSection());
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
                        `<option value="${option.KElabel}" data-title="${option.KEtitle}">${option.KElabel} - ${option.KEtitle}</option>`
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
                        `<option value="${option.pathwayID}" data-title="${option.pathwayTitle}">${option.pathwayID} - ${option.pathwayTitle}</option>`
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

        const formData = {
            ke_id: $("#ke_id").val(),
            ke_title: $("#ke_id option:selected").data("title"),
            wp_id: $("#wp_id").val(),
            wp_title: $("#wp_id option:selected").data("title"),
            connection_type: $("#connection_type").val(),
            confidence_level: $("#confidence_level").val()
        };

        // Validate required fields
        if (!formData.ke_id || !formData.wp_id) {
            this.showMessage("Please select both a Key Event and a Pathway", "error");
            return;
        }

        if (!formData.connection_type || !formData.confidence_level) {
            this.showMessage("Please complete the confidence assessment", "error");
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
                <div class="confirmation-section">
                    <p>Do you want to add this new KE-WP pair?</p>
                    <button id="confirm-submit" class="btn btn-success">Yes, Add Entry</button>
                    <button id="cancel-submit" class="btn btn-secondary">Cancel</button>
                </div>
            </div>
        `;
        
        $("#existing-entries").html(tableHTML);

        // Handle confirmation buttons
        $("#confirm-submit").on('click', () => {
            this.submitEntry(formData);
        });

        $("#cancel-submit").on('click', () => {
            $("#existing-entries").html("");
        });
    }

    showMappingPreview(formData) {
        let previewHTML = `
            <div class="existing-entries-container">
                <h3>Confirm Your Mapping</h3>
                <p>Please review your mapping details before submitting:</p>
                <div class="mapping-preview">
                    <div class="preview-section">
                        <h4>Key Event Information</h4>
                        <p><strong>KE ID:</strong> ${formData.ke_id}</p>
                        <p><strong>KE Title:</strong> ${formData.ke_title}</p>
                    </div>
                    <div class="preview-section">
                        <h4>Pathway Information</h4>
                        <p><strong>WP ID:</strong> ${formData.wp_id}</p>
                        <p><strong>WP Title:</strong> ${formData.wp_title}</p>
                    </div>
                    <div class="preview-section">
                        <h4>Mapping Details</h4>
                        <p><strong>Connection Type:</strong> ${formData.connection_type.charAt(0).toUpperCase() + formData.connection_type.slice(1)}</p>
                        <p><strong>Confidence Level:</strong> ${formData.confidence_level.charAt(0).toUpperCase() + formData.confidence_level.slice(1)}</p>
                    </div>
                </div>
                <div class="confirmation-section">
                    <p><strong>Are you sure you want to submit this mapping?</strong></p>
                    <button id="confirm-final-submit" class="btn btn-success">Yes, Submit Mapping</button>
                    <button id="cancel-final-submit" class="btn btn-secondary">Cancel</button>
                </div>
            </div>
        `;
        
        $("#existing-entries").html(previewHTML);

        // Handle confirmation buttons
        $("#confirm-final-submit").on('click', () => {
            this.submitEntry(formData);
        });

        $("#cancel-final-submit").on('click', () => {
            $("#existing-entries").html("");
        });
    }

    submitEntry(formData) {
        $.post("/submit", formData)
            .done((response) => {
                this.showMessage(response.message, "success");
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

    toggleAssessmentSection() {
        const keSelected = $("#ke_id").val();
        const wpSelected = $("#wp_id").val();
        if (keSelected && wpSelected) {
            $("#confidence-guide").show();
            $("#confidence-guide")[0].scrollIntoView({ behavior: 'smooth' });
        } else {
            $("#confidence-guide").hide();
            this.resetGuide();
        }
    }

    resetGuide() {
        const sections = ["#step2", "#step3", "#step4", "#step5", "#step6", "#step2b"];
        sections.forEach(id => {
            $(id).hide().find("select").val("");
        });
        $("#evaluateBtn").hide();
        $("#ca-result").text("");
        $("#auto-confidence").text("—");
        $("#auto-connection").text("—");
        $("#confidence_level").val("");
        $("#connection_type").val("");
        this.stepAnswers = {};
    }

    resetForm() {
        $("#ke_id, #wp_id").val("").trigger('change');
        this.resetGuide();
        $("#message").text("");
    }

    showMessage(message, type = "info") {
        const color = type === "error" ? "red" : type === "success" ? "green" : "blue";
        $("#message").text(message).css("color", color);
        
        // Auto-hide success messages after 5 seconds
        if (type === "success") {
            setTimeout(() => {
                $("#message").fadeOut();
            }, 5000);
        }
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