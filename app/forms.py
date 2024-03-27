from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    PasswordField,
    BooleanField,
    SelectField,
    IntegerField,
    TextAreaField,
)
from flask_wtf.file import FileField, FileRequired, FileAllowed

from wtforms.validators import (
    DataRequired,
    Length,
    EqualTo,
    Email,
    Regexp,
    ValidationError,
    Optional,
)
import phonenumbers
from app.models import User


# ========================================
# USER LOGIN
# ========================================


class LoginForm(FlaskForm):
    """Login Form"""

    username = StringField(
        "Username",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"autofocus": True, "placeholder": "arya"},
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=20),
            # Regexp(
            #     r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$",
            #     message="Password must be at least 8 characters long and "
            #     "contain at least one letter and one number.",
            # ),
        ],
        render_kw={"placeholder": "Example:  kavyaarya123."},
    )
    remember_me = BooleanField("Keep me logged in", default=True)
    submit = SubmitField("Log In")


# ========================================
# END OF USER LOGIN
# ========================================


# ========================================
# PASSWORD RESET
# ========================================


class RequestPasswordResetForm(FlaskForm):
    """User can request for a password reset"""

    email = StringField(
        "Email",
        validators=[DataRequired(), Email()],
        render_kw={
            "autofocus": True,
            "placeholder": "You have access to this email address",
        },
    )
    submit = SubmitField("Request Password Reset")


class ResetPasswordForm(FlaskForm):
    """User can change their password"""

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=20),
            # Regexp(
            #     r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$",
            #     message="Password must be at least 8 characters long and "
            #     "contain at least one letter and one number.",
            # ),
        ],
        render_kw={"autofocus": True, "placeholder": "Password"},
    )
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Reset Password")


# ========================================
# END OF PASSWORD RESET
# ========================================


# ========================================
# USER REGISTRATION

# Define a base form
# Let children inherit the buyer form
# ========================================


class UserForm(FlaskForm):
    """General User Data"""

    first_name = StringField(
        "First Name",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"autofocus": True, "placeholder": "Kavya"},
    )
    last_name = StringField(
        "Last Name",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"placeholder": "Morakhiya"},
    )
    username = StringField(
        "Username",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"placeholder": "morakhiyakavya"},
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "morakhiyakavya@gmail.com"},
    )
    phone_number = StringField(
        "Phone Number", validators=[DataRequired(), Length(min=2, max=10)],
        render_kw={"placeholder": "9876543210"},
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=20),
            # Regexp(
            #     r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$",
            #     message="Password must be at least 8 characters long and "
            #     "contain at least one letter and one number.",
            # ),
        ],
        render_kw={"placeholder": "Example:  #kavyaarya123#."},
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password")],
        render_kw={"placeholder": "Confirm Your Above Password"},
    )

    def validate_username(self, username):
        """Check if username already exists"""
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("Please use a different username.")

    def validate_email(self, email):
        """Check if email already exists"""
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Please use a different email address.")

    def validate_phone(self, phone):
        p = phonenumbers.parse(phone.data)
        try:
            if not phonenumbers.is_valid_number(p):
                raise ValueError()
        except (phonenumbers.phonenumberutil.NumberParseException, ValueError) as exc:
            raise ValidationError("Invalid phone number.\n\n", exc) from exc


# Change Needed
class BuyerRegistrationForm(UserForm):
    """buyer Registration Form"""

    current_residence = StringField(
        "Current Residence",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"placeholder": "Ahmedabad, Gujarat"},
    )
    submit = SubmitField("Register")


# Change Needed
class SellerRegistrationForm(UserForm):
    """seller Registration Form"""

    current_residence = StringField(
        "Current Residence",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"placeholder": "Ahmedabad, Gujarat"},
    )
    submit = SubmitField("Register")


# Change Needed
class AdminRegistrationForm(UserForm):
    """Admin Registration Form"""

    current_residence = StringField(
        "Current Residence",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"placeholder": "Ahmedabad, Gujarat"},
    )
    submit = SubmitField("Register")


# ========================================
# END OF USER REGISTRATION
# ========================================


# ========================================
# PRODUCT RELATED FORMS
# ========================================

class ProductForm(FlaskForm):
    """Product Form"""

    name = StringField(
        "Name",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"autofocus": True, "placeholder": "Product Name"},
    )
    description = StringField(
        "Description",
        validators=[DataRequired()],
        render_kw={"placeholder": "Description"},
    )

    submit = SubmitField("Add Product")

class EditProductForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"autofocus": True, "placeholder": "Product Name"},
    )
    description = StringField(
        "Description",
        validators=[DataRequired()],
        render_kw={"placeholder": "Description"},
    )

    submit = SubmitField("Update", render_kw={"class": "btn btn-danger"})

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("Please use a different username.")

class PanForm(FlaskForm):
    """Pan Form"""

    name = StringField(
        "Name",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"autofocus": True, "placeholder": "Name"},
    )
    pan_number = StringField(
        "Pan Number",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"placeholder": "Pan Number"},
    )
    dp_id = StringField(
        "DP ID",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"placeholder": "DP ID"},
    )
    submit = SubmitField("Add Pan")    

class DetailForm(FlaskForm):
    """Subject Form"""

    subject = SelectField(
        "Subject",
        choices=[("Subject 1", "Subject 1"), ("Subject 2", "Subject 2")],
        validators=[DataRequired()],
        default="Subject 1"  # Set the default choice
    )
    formtype = SelectField(
        "Form Type",
        choices=[("Retail", "Retail"), ("HNI", "HNI"), ("SHNI", "SHNI")],
        validators=[DataRequired()],
        default="Retail"  # Set the default choice
    )
    price = IntegerField(
        "Price",
        validators=[DataRequired()],
        render_kw={"placeholder": "Price"},
    )
    quantity = IntegerField(
        "Quantity",
        validators=[DataRequired()],
        render_kw={"placeholder": "Quantity"},
    )
    
    submit = SubmitField("Add Details")


# ========================================
# END OF PRODUCT RELATED FORMS
# ========================================

# ========================================
# ALLOTMENT Related Forms
# ========================================

class AllotmentForm(FlaskForm):
    """Allotment Form"""

    ipo = StringField(
        "Ipo Name",
        validators=[DataRequired(), Length(1, 64)],
        render_kw={"autofocus": True, "placeholder": "Allotment Name", "id": "ipo_field"}
    )
    listing_On = SelectField(
        "Listing On",
        choices=[("linkin", "linkin"), ("kfintech", "kfintech"), ("bigshare", "bigshare"), ("skyline", "skyline"), ("purva", "purva")],
        validators=[DataRequired()],
        default="linkin",
        render_kw={"id": "listing_on_field"}
    )
    pan_Column = StringField(
        "Pan Column",
        validators=[DataRequired()],
        render_kw={"placeholder": "Pan Column(eg: A or 1)", "id": "pan_column_field"}
    )
    start_Row = IntegerField(
        "Pan Start Row",
        validators=[DataRequired()],
        render_kw={"placeholder": "Pan Start Row(eg: 2)", "id": "start_row_field"}
    )
    end_Row = IntegerField(
        "Pan End Row",
        validators=[Optional()],
        render_kw={"placeholder": "Pan End Row(eg: 100, you can leave it blank)", "id": "end_row_field"}
    )
    excel_file = FileField(
        'Upload Excel File',
        validators=[
            FileRequired(),
            FileAllowed(['xls', 'xlsx'], 'Excel files only!')
        ],
        render_kw={"id": "excel_file_field"}
    )
    submit = SubmitField(
        "Add Allotment",
        render_kw={"id": "submit_btn"}
    )

# ========================================
# END OF ALLOTMENT RELATED FORMS
# ========================================


# ========================================
# TWO FACTOR AUTHENTICATION
# ========================================

# Verify token sent


class VerifyForm(FlaskForm):
    """token verification form"""

    token = StringField(
        "Token",
        validators=[DataRequired()],
        render_kw={"autofocus": True, "placeholder": "Enter token sent"},
    )
    submit = SubmitField("Verify")


# Disable 2fa


class DisableForm(FlaskForm):
    """User can disable 2FA"""

    submit = SubmitField("Disable")


# ========================================
# END OF TWO FACTOR AUTHENTICATION
# ========================================


# ========================================
# EMAIL
# ========================================


class EmailForm(FlaskForm):
    subject = StringField(
        "Subject",
        validators=[DataRequired()],
        render_kw={"autofocus": True, "placeholder": "Markdown enabled"},
    )
    body = TextAreaField(
        "Body",
        validators=[DataRequired()],
        render_kw={"placeholder": "Markdown enabled"},
    )
    closing = SelectField(
        "Closing",
        choices=[("Kind Regards", "Kind Regards")],
        validators=[DataRequired()],
    )
    signature = SelectField("Signature", choices=[], validators=[DataRequired()])
    submit = SubmitField("Create Email")


# ========================================
# END OF EMAIL
# ========================================


# Unsubscribe from newsletter


# Change Needed
class UnsubscribeForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()],
        render_kw={"autofocus": True, "placeholder": "Your subscription email"},
    )
    submit = SubmitField("Unsubscribe")


# =============
# Profile Edits
# =============


class EditUsernameForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=2, max=30)]
    )
    submit = SubmitField("Update", render_kw={"class": "btn btn-danger"})

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("Please use a different username.")


class EditEmailForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[DataRequired(), Email(), Length(min=2, max=64)],
        render_kw={"placeholder": "You have access to this email address"},
    )
    submit = SubmitField("Update", render_kw={"class": "btn btn-danger"})

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Please use a different email.")


class EditPhoneForm(FlaskForm):
    phone = StringField(
        "Phone Number", validators=[DataRequired(), Length(min=2, max=30)]
    )
    submit = SubmitField("Update", render_kw={"class": "btn btn-danger"})

    def validate_phone(self, phone):
        p = phonenumbers.parse(phone.data)
        try:
            if not phonenumbers.is_valid_number(p):
                raise ValueError()
        except (phonenumbers.phonenumberutil.NumberParseException, ValueError):
            raise ValidationError("Invalid phone number.")


# buyer


# Change Needed
class EditResidenceForm(FlaskForm):
    residence = StringField(
        "Residence", validators=[DataRequired(), Length(min=2, max=30)]
    )
    submit = SubmitField("Update")


# seller


# Change Needed
class EditSchoolForm(FlaskForm):
    school = StringField("School", validators=[DataRequired(), Length(min=2, max=30)])
    submit = SubmitField("Update")


# =============
# End of Profile Edits
# =============

# =================================
# End of Profile Edits
# =================================
