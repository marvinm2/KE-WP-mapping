"""
Tests for GO and KE directionality detection functions.

Tests both detect_go_direction() and detect_ke_direction() covering
all behavioral categories: positive, negative, unspecified, and ambiguous.
"""

import pytest
from src.utils.text import detect_go_direction, detect_ke_direction


# ==============================================================================
# detect_go_direction tests
# ==============================================================================

class TestDetectGoDirection:
    """Tests for GO term direction detection via prefix matching."""

    def test_positive_regulation(self):
        assert detect_go_direction("positive regulation of apoptotic process") == "positive"

    def test_positive_regulation_cell_growth(self):
        assert detect_go_direction("positive regulation of cell growth") == "positive"

    def test_negative_regulation(self):
        assert detect_go_direction("negative regulation of cell growth") == "negative"

    def test_negative_regulation_apoptosis(self):
        assert detect_go_direction("negative regulation of apoptotic process") == "negative"

    def test_plain_regulation_unspecified(self):
        """Plain 'regulation of X' without positive/negative prefix -> unspecified."""
        assert detect_go_direction("regulation of transcription") == "unspecified"

    def test_no_regulation_unspecified(self):
        """Term with no regulation prefix -> unspecified."""
        assert detect_go_direction("apoptotic process") == "unspecified"

    def test_empty_string_unspecified(self):
        assert detect_go_direction("") == "unspecified"

    def test_none_like_empty_unspecified(self):
        """Whitespace-only string -> unspecified."""
        assert detect_go_direction("   ") == "unspecified"

    def test_case_insensitive_positive(self):
        """Detection should be case-insensitive."""
        assert detect_go_direction("Positive regulation of X") == "positive"

    def test_case_insensitive_negative(self):
        """Detection should be case-insensitive."""
        assert detect_go_direction("Negative regulation of X") == "negative"

    def test_positive_short_name(self):
        assert detect_go_direction("positive regulation of X") == "positive"

    def test_negative_short_name(self):
        assert detect_go_direction("negative regulation of X") == "negative"

    def test_unrelated_term_unspecified(self):
        assert detect_go_direction("mitochondrial ATP synthesis") == "unspecified"

    def test_regulation_without_positive_negative_unspecified(self):
        assert detect_go_direction("regulation of cell proliferation") == "unspecified"


# ==============================================================================
# detect_ke_direction tests
# ==============================================================================

class TestDetectKeDirection:
    """Tests for KE title direction detection via regex pattern matching."""

    # Positive cases
    def test_increase_positive(self):
        assert detect_ke_direction("Increase in ROS production") == "positive"

    def test_activation_positive(self):
        assert detect_ke_direction("Activation of EGFR signaling") == "positive"

    def test_elevated_positive(self):
        assert detect_ke_direction("Elevated cortisol levels") == "positive"

    def test_upregulation_positive(self):
        assert detect_ke_direction("Upregulation of HMOX1") == "positive"

    def test_induction_positive(self):
        assert detect_ke_direction("Induction of apoptosis") == "positive"

    def test_enhancement_positive(self):
        assert detect_ke_direction("Enhancement of inflammatory response") == "positive"

    def test_accumulation_positive(self):
        assert detect_ke_direction("Accumulation of reactive oxygen species") == "positive"

    def test_formation_positive(self):
        assert detect_ke_direction("Formation of DNA adducts") == "positive"

    def test_generation_positive(self):
        assert detect_ke_direction("Generation of superoxide") == "positive"

    def test_gain_positive(self):
        assert detect_ke_direction("Gain of function mutation") == "positive"

    def test_excessive_positive(self):
        assert detect_ke_direction("Excessive ROS production") == "positive"

    # Negative cases
    def test_decrease_negative(self):
        assert detect_ke_direction("Decreased mitochondrial function") == "negative"

    def test_inhibition_negative(self):
        assert detect_ke_direction("Inhibition of complex I") == "negative"

    def test_suppression_negative(self):
        assert detect_ke_direction("Suppression of immune response") == "negative"

    def test_reduced_negative(self):
        assert detect_ke_direction("Reduced ATP production") == "negative"

    def test_disruption_negative(self):
        assert detect_ke_direction("Disruption of mitochondrial membrane") == "negative"

    def test_impairment_negative(self):
        assert detect_ke_direction("Impairment of lysosomal function") == "negative"

    def test_depletion_negative(self):
        assert detect_ke_direction("Depletion of glutathione") == "negative"

    def test_loss_negative(self):
        assert detect_ke_direction("Loss of barrier integrity") == "negative"

    def test_deficient_negative(self):
        assert detect_ke_direction("Deficient DNA repair") == "negative"

    def test_downregulation_negative(self):
        assert detect_ke_direction("Downregulation of NRF2") == "negative"

    # Unspecified cases
    def test_altered_unspecified(self):
        """'Altered' is ambiguous, must NOT trigger direction detection."""
        assert detect_ke_direction("Altered gene expression") == "unspecified"

    def test_changes_unspecified(self):
        """'Changes' is ambiguous."""
        assert detect_ke_direction("Changes in membrane potential") == "unspecified"

    def test_neutral_biology_unspecified(self):
        """Neutral biological term with no directional signal."""
        assert detect_ke_direction("Cell proliferation") == "unspecified"

    def test_binding_unspecified(self):
        """'Binding' should not trigger direction."""
        assert detect_ke_direction("Binding of ligand to receptor") == "unspecified"

    def test_release_unspecified(self):
        """'Release' should not trigger direction."""
        assert detect_ke_direction("Release of cytokines") == "unspecified"

    def test_presence_unspecified(self):
        """'Presence' should not trigger direction."""
        assert detect_ke_direction("Presence of DNA damage") == "unspecified"

    def test_empty_string_unspecified(self):
        assert detect_ke_direction("") == "unspecified"

    # Ambiguous (both positive and negative terms)
    def test_ambiguous_both_directions_unspecified(self):
        """When both positive AND negative terms detected -> unspecified."""
        assert detect_ke_direction("Activation and Inhibition of pathway") == "unspecified"

    def test_ambiguous_increase_decrease_unspecified(self):
        """Both increase and decrease in same title -> unspecified."""
        assert detect_ke_direction("Increase in X and decrease in Y") == "unspecified"

    def test_abnormal_unspecified(self):
        """'Abnormal' is ambiguous, must NOT trigger direction."""
        assert detect_ke_direction("Abnormal cell growth") == "unspecified"

    def test_lack_unspecified(self):
        """'Lack' should not trigger direction by itself."""
        assert detect_ke_direction("Lack of response") == "unspecified"
