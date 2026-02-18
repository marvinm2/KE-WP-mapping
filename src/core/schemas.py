"""
Input validation schemas using Marshmallow
"""
import re

from marshmallow import Schema, ValidationError, fields, validate, validates


class MappingSchema(Schema):
    """Schema for KE-WP mapping submissions"""

    ke_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(r"^KE\s+\d+$", error="KE ID must be in format 'KE number'"),
        ],
    )
    ke_title = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    wp_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(r"^WP\d+$", error="WP ID must be in format 'WPnumber'"),
        ],
    )
    wp_title = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    connection_type = fields.Str(
        required=True,
        validate=validate.OneOf(
            ["causative", "responsive", "other", "undefined"],
            error="Invalid connection type",
        ),
    )
    confidence_level = fields.Str(
        required=True,
        validate=validate.OneOf(
            ["low", "medium", "high"], error="Invalid confidence level"
        ),
    )


class ProposalSchema(Schema):
    """Schema for proposal submissions"""

    entry = fields.Str(required=True)  # JSON string of entry data
    userName = fields.Str(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(
                r"^[a-zA-Z0-9\s\-\.\'_]+$",
                error="Name can only contain letters, numbers, spaces, hyphens, dots, apostrophes, and underscores",
            ),
        ],
    )
    userEmail = fields.Email(required=True)
    userAffiliation = fields.Str(
        required=True, validate=validate.Length(min=1, max=200)
    )
    deleteEntry = fields.Str(missing="", validate=validate.OneOf(["", "on"]))
    changeConfidence = fields.Str(
        missing="", validate=validate.OneOf(["", "low", "medium", "high"])
    )
    changeType = fields.Str(
        missing="",
        validate=validate.OneOf(["", "causative", "responsive", "undefined"]),
    )

    @validates("entry")
    def validate_entry_json(self, value):
        """Validate that entry is valid JSON with required fields"""
        import json

        try:
            # Handle double-serialized JSON
            if value.startswith('"') and value.endswith('"'):
                value = json.loads(value)  # First deserialization
            entry_data = json.loads(
                value.replace("'", '"')
            )  # Second deserialization with quote fix

            if not isinstance(entry_data, dict):
                raise ValidationError("Entry must be a JSON object")

            required_fields = ["ke_id", "wp_id"]
            missing_fields = []

            for field in required_fields:
                # Check both snake_case and original formats
                if not (
                    entry_data.get(field)
                    or entry_data.get(field.replace("_", "").upper())
                ):
                    missing_fields.append(field)

            if missing_fields:
                raise ValidationError(
                    f"Entry missing required fields: {missing_fields}"
                )

        except json.JSONDecodeError as e:
            raise ValidationError(f"Entry must be valid JSON: {str(e)}")


class GoMappingSchema(Schema):
    """Schema for KE-GO mapping submissions"""

    ke_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(r"^KE\s+\d+$", error="KE ID must be in format 'KE number'"),
        ],
    )
    ke_title = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    go_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=10, max=20),
            validate.Regexp(
                r"^GO:\d{7}$", error="GO ID must be in format 'GO:0000000'"
            ),
        ],
    )
    go_name = fields.Str(required=True, validate=validate.Length(min=1, max=500))
    connection_type = fields.Str(
        required=True,
        validate=validate.OneOf(
            ["describes", "involves", "related", "context"],
            error="Invalid connection type",
        ),
    )
    confidence_level = fields.Str(
        required=True,
        validate=validate.OneOf(
            ["low", "medium", "high"], error="Invalid confidence level"
        ),
    )


class GoCheckEntrySchema(Schema):
    """Schema for checking existing GO entries"""

    ke_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(r"^KE\s+\d+$", error="KE ID must be in format 'KE number'"),
        ],
    )
    go_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=10, max=20),
            validate.Regexp(
                r"^GO:\d{7}$", error="GO ID must be in format 'GO:0000000'"
            ),
        ],
    )


class AdminNotesSchema(Schema):
    """Schema for admin notes in proposal management"""

    admin_notes = fields.Str(missing="", validate=validate.Length(max=1000))


class CheckEntrySchema(Schema):
    """Schema for checking existing entries"""

    ke_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(r"^KE\s+\d+$", error="KE ID must be in format 'KE number'"),
        ],
    )
    wp_id = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(r"^WP\d+$", error="WP ID must be in format 'WPnumber'"),
        ],
    )


class SecurityValidation:
    """Additional security validation utilities"""

    @staticmethod
    def sanitize_string(value: str, max_length: int = 500) -> str:
        """Sanitize string input by removing potentially harmful characters"""
        if not isinstance(value, str):
            return str(value)

        # Remove null bytes and control characters except common whitespace
        sanitized = "".join(
            char for char in value if ord(char) >= 32 or char in "\t\n\r"
        )

        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized.strip()

    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate GitHub or guest username format"""
        if not isinstance(username, str):
            return False

        # Guest usernames: guest-<label> where label is alphanumeric with hyphens/underscores
        if username.startswith("guest-"):
            guest_label = username[6:]
            return bool(re.match(r"^[a-zA-Z0-9_-]{3,50}$", guest_label))

        # GitHub username rules: alphanumeric, hyphens, max 39 chars, no consecutive hyphens
        pattern = r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$"
        return bool(re.match(pattern, username))

    @staticmethod
    def validate_email_domain(email: str) -> bool:
        """Basic email domain validation (additional to Marshmallow's email validation)"""
        if not isinstance(email, str) or "@" not in email:
            return False

        domain = email.split("@")[1]
        # Basic domain validation - at least one dot and valid characters
        return bool(
            re.match(
                r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$",
                domain,
            )
        )


def validate_request_data(schema_class, data):
    """
    Validate request data using the provided schema

    Args:
        schema_class: Marshmallow schema class to use for validation
        data: Data to validate (typically request.form or request.json)

    Returns:
        tuple: (is_valid: bool, validated_data: dict, errors: dict)
    """
    schema = schema_class()

    try:
        validated_data = schema.load(data)
        return True, validated_data, {}
    except ValidationError as e:
        return False, {}, e.messages
