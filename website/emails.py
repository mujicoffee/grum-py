from flask_mail import Message
from . import mail
from datetime import datetime, timedelta

def send_otp_email(recipient_name, recipient_email, otp):
    # Create a Message object with the subject, sender and recipient
    msg = Message('Your One-Time Password (OTP)', sender='flask.grumpy@gmail.com', recipients=[recipient_email])
    # Add the message body
    msg.html = f"""
    <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>Welcome to grumPY! Please use the following One-Time Password (OTP) to complete your login process:</p>
            <p style="font-size: 1.2em;"><strong>OTP: {otp}</strong></p>
            <p style="color: red;">Do not share this OTP with anyone.</p>
            <p>Please note that this code will expire in 5 minutes.</p>
            <p>If you did not request this OTP, please ignore this email.</p>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the addressee, do not disclose, copy, circulate or in any other way use or rely on the information contained in this email or any attachments. 
                If received in error, please delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """
    # Send the email
    mail.send(msg)

def send_first_login_email(recipient_name, recipient_email):
    # Retrieve the current timestamp
    timestamp = datetime.now().strftime('%d/%m/%y %I:%M:%S %p')
    # Create a Message object with the subject, sender and recipient
    msg = Message('First Login Confirmation', sender='flask.grumpy@gmail.com', recipients=[recipient_email])
    # Add the message body
    msg.html = f""" 
    <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>You have successfully changed your password on your first login at <strong>{timestamp}</strong>.</p>
            <p style="color: red;">If you initiated this change, there is no further action needed and you can safely disregard this email.</p>
            <p>As a reminder, all recent password changes and resets must wait for 24 hours before a new request can be initiated.</p>
            <p>
                Remember that your account security is crucial to us. 
                In addition, we have sent you a separate email containing a important disclaimer about virus liability and security precautions. 
                Please review that email carefully to understand our policies and your responsibilities regarding the security of our communications.
            </p>
            <p>Thanks for using grumPY!</p>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the addressee, do not disclose, copy, circulate or in any other way use or rely on the information contained in this email or any attachments. 
                If received in error, please delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """ 
    # Send the email
    mail.send(msg)

def send_suspicious_login_email(recipient_name, recipient_email, timestamps):
    
    def ordinal_suffix(n):
        suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = suffixes.get(n % 10, 'th')
        return suffix
    
    # Calculate the time when the user can log in again
    lockout_end_time = datetime.now() + timedelta(minutes=10)
    lockout_end_formatted = lockout_end_time.strftime('%d/%m/%Y %I:%M:%S %p')

    # Format the timestamps to 12-hour format
    formatted_timestamps = [
        datetime.strptime(timestamp, '%d/%m/%Y %H:%M:%S').strftime('%d/%m/%Y %I:%M:%S %p')
        for timestamp in timestamps
    ]

    # Define the alternating row colors for the table
    row_colors = ['#f8f9fa', '#e9ecef']
    # Create the table rows for the failed login attempts
    rows = ''.join(
        f"""
        <tr style="background-color:{row_colors[i % 2]};">
            <td style="padding: 8px;">{i + 1}{ordinal_suffix(i + 1)} Login</td>
            <td style="padding: 8px;">{formatted_timestamps[i]}</td>
        </tr>
        """
        for i in range(len(formatted_timestamps))
    )
    
    # Create a Message object with the subject, sender, and recipient
    msg = Message('Suspicious Login Activity', sender='flask.grumpy@gmail.com', recipients=[recipient_email])
    # Add the message body
    msg.html = f"""
    <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>
                We have detected multiple failed login attempts on your grumPY account. 
                As a security measure, we have temporarily suspended all logins under your account for <strong>10 minutes</strong>.
            </p>
            <p>You will be able to login in again after <strong>{lockout_end_formatted}</strong>.</p>
            <p>The details of the failed login attempts were as follows:</p>
            <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #343a40; color: #fff;">
                    <th style="width: 50%;">Attempt</th>
                    <th style="width: 50%;">Date & Time</th>
                </tr>
                {rows}
            </table>
            <p style="color: red;">
                If you did not initiate these login attempts or if you find this activity unusual, please take immediate action to secure your account. 
                Consider updating your password as an additional precaution.
            </p>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the addressee, do not disclose, copy, circulate or in any other way use or rely on the information contained in this email or any attachments. 
                If received in error, please delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """
    # Send the email
    mail.send(msg)

def send_account_deactivation_email(recipient_name, recipient_email):
    # Create a Message object with the subject, sender and recipient
    msg = Message('grumPY Account Deactivation', sender='flask.grumpy@gmail.com', recipients=[recipient_email])
    # Add the message body
    msg.html = f"""
    <html>
        <body>
            <div style="background-color: #FFD700; padding: 10px; border: 1px solid #ccc; margin-top: 20px;">
                <p style="margin: 0; font-weight: bold;">WARNING:</p>
                <p style="margin: 0;">
                    While grumPY takes reasonable precautions to ensure that this email is free from viruses, we cannot guarantee its absolute security. 
                    The recipient is responsible for scanning this email and any attachments for viruses. grumPY accepts no liability for any loss or damage caused by viruses or errors in transmission. 
                    Please review the contents carefully and take the necessary precautions.
                </p>
            </div>
            <p>Dear {recipient_name},</p>
            <p>
                We regret to inform you that your grumPY account has been deactivated due to several unsuccessful login attempts.
                Our security protocols automatically trigger this action to protect your account from unauthorised access.
            </p>
            <p>As part of our commitment to security, we take such incidents seriously to safeguard your information.</p>
            <p style="color: red;">If you believe this deactivation was in error or wish to reactivate your account, please reset your password 
            <strong><a href="http://127.0.0.1:5000/forget-password">here</a></strong>.</p>
            <p>Once your password is reset, your account will be reactivated automatically.</p>
            <p>Thank you for your understanding and cooperation.</p>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the addressee, do not disclose, copy, circulate or in any other way use or rely on the information contained in this email or any attachments. 
                If received in error, please delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """
    # Send the email
    mail.send(msg)

def send_forget_password_email(recipient_name, recipient_email, token):
    # Create a Message object with the subject, sender and recipient
    msg = Message('Forgot Your Password?', sender='flask.grumpy@gmail.com', recipients=[recipient_email])
    # Add the message body
    msg.html = f"""
    <html>
        <body>
            <div style="background-color: #FFD700; padding: 10px; border: 1px solid #ccc; margin-top: 20px;">
                <p style="margin: 0; font-weight: bold;">WARNING:</p>
                <p style="margin: 0;">
                    While grumPY takes reasonable precautions to ensure that this email is free from viruses, we cannot guarantee its absolute security. 
                    The recipient is responsible for scanning this email and any attachments for viruses. grumPY accepts no liability for any loss or damage caused by viruses or errors in transmission. 
                    Please review the contents carefully and take the necessary precautions.
                </p>
            </div>
            <p>Dear {recipient_name},</p>
            <p>
                We have received a request for a password reset on your grumPY account.
                To proceed with the password reset, please follow the instructions below:
            </p>
            <ol>
                <li>
                    <span>Click on the link to reset your password:</span>
                    <strong><a href="http://127.0.0.1:5000/reset-password/{token}">Reset Password</a></strong>
                </li>
                <li style="margin-top: 10px; margin-bottom: 20px;">
                    Note that this link will expire in 20 minutes. 
                    After that, you will need to submit a new request to reset your password.
                </li>
            </ol>
            <p style="color: red;">If you did not request this password reset, please disregard this email. Your password will not change unless you use the link above.</p>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the addressee, do not disclose, copy, circulate or in any other way use or rely on the information contained in this email or any attachments. 
                If received in error, please delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """
    # Send the email
    mail.send(msg)

def send_reset_password_email(recipient_name, recipient_email):
    # Retrieve the current timestamp
    timestamp = datetime.now().strftime('%d/%m/%y %I:%M:%S %p')
    # Create a Message object with the subject, sender and recipient
    msg = Message('Successful Password Reset', sender='flask.grumpy@gmail.com', recipients=[recipient_email])
    # Add the message body
    msg.html = f"""
    <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>Please note that your password has been successfully reset at <strong>{timestamp}</strong>.</p>
            <p style="color: red;">If you initiated this change, there is no further action needed and you can safely disregard this email.</p>
            <p>As a reminder, all recent password changes and resets must wait for 24 hours before a new request can be initiated.</p>
            <p>Thanks for using grumPY!</p>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the addressee, do not disclose, copy, circulate or in any other way use or rely on the information contained in this email or any attachments. 
                If received in error, please delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """
    # Send the email
    mail.send(msg)

def send_reset_password_suspension_email(recipient_email, recipient_name, timestamp):
    # Create a Message object with the subject, sender, and recipient
    msg = Message('Temporary Password Reset Suspension', sender='flask.grumpy@gmail.com', recipients=[recipient_email])
    
    # Format the timestamp for display
    formatted_timestamp = timestamp.strftime('%d/%m/%y %I:%M:%S %p')

    # Add the message body
    msg.html = f"""
    <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>We would like to inform you about an important security measure related to your recent password change.</p>
            <p>
                After changing your password, our system enforces a 24-hour waiting period before you can reset it again. This is a precautionary step to enhance your account's security.
                By delaying password resets, we prevent potential abuse or unauthorised access. It ensures that any recent changes are intentional and not accidental.
            </p>
            <p>Rest assured your new password is in effect, and you can continue using it for all your logins during this period.</p>
            <p style="color: red;">If you would like to reset your password, it will be available for reset after <strong>{formatted_timestamp}</strong>.</p>
            <p>Thank you for your understanding and cooperation.</p>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the addressee, do not disclose, copy, circulate or in any other way use or rely on the information contained in this email or any attachments. 
                If received in error, please delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """
    # Send the email
    mail.send(msg)

def send_student_account_setup_email(recipient_email, recipient_name, password):
    # Create a Message object with the subject, sender and recipient
    msg = Message('[IMPORTANT] grumPY Student Account Setup', sender='flask.grumpy@gmail.com', recipients=[recipient_email])
    # Add the message body
    msg.html = f"""
    <html>
        <body>
            <div style="background-color: #FFD700; padding: 10px; border: 1px solid #ccc; margin-top: 20px;">
                <p style="margin: 0; font-weight: bold;">WARNING:</p>
                <p style="margin: 0;">
                    While grumPY takes reasonable precautions to ensure that this email is free from viruses, we cannot guarantee its absolute security. 
                    The recipient is responsible for scanning this email and any attachments for viruses. grumPY accepts no liability for any loss or damage caused by viruses or errors in transmission. 
                    Please review the contents carefully and take the necessary precautions.
                </p>
            </div>
            <p>Dear {recipient_name},</p>
            <p>Welcome to grumPY! We are excited to have you on board, before you begin here are your temporary login credentials:</p>
            <p style="font-weight: bold;">Temporary Login Credentials:</p>
            <ul>
                <li>Email Address: <strong>{recipient_email}</strong></li>
                <li>Password: <strong>{password}</strong></li>
            </ul>
            <p style="color: red;">Please note that this password is only valid for your first login.</p>
            <p>For security reasons, you are required to change your password after logging in <strong><a href="http://127.0.0.1:5000">here</a></strong>.</p>  
            <p>On behalf of the grumPY team, we hope that you will have an exciting Flask journey!</p>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the addressee, do not disclose, copy, circulate, or in any other way use or rely on the information contained in this email or any attachments. 
                If received in error, please delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """
    # Send the email
    mail.send(msg)

def send_staff_account_setup_email(recipient_email, recipient_name, password):
    # Create a Message object with the subject, sender and recipient
    msg = Message('[IMPORTANT] grumPY Staff Account Setup', sender='flask.grumpy@gmail.com', recipients=[recipient_email])
    # Add the message body
    msg.html = f"""
    <html>
        <body>
            <div style="background-color: #FFD700; padding: 10px; border: 1px solid #ccc; margin-top: 20px;">
                <p style="margin: 0; font-weight: bold;">WARNING:</p>
                <p style="margin: 0;">
                    While grumPY takes reasonable precautions to ensure that this email is free from viruses, we cannot guarantee its absolute security. 
                    The recipient is responsible for scanning this email and any attachments for viruses. grumPY accepts no liability for any loss or damage caused by viruses or errors in transmission. 
                    Please review the contents carefully and take the necessary precautions.
                </p>
            </div>
            <p>Dear {recipient_name},</p>
            <p>
                We are pleased to inform you that your staff account has been successfully created in the grumPY system. 
                To ensure you can access your account promptly, please find your temporary login credentials below:
            </p>
            <p style="font-weight: bold;">Temporary Login Credentials:</p>
            <ul>
                <li>Email Address: <strong>{recipient_email}</strong></li>
                <li>Password: <strong>{password}</strong></li>
            </ul>
            <p style="font-weight: bold;">Instructions to access your account:</p>
            <ol>
                <li>Please visit our login page <strong><a href="http://127.0.0.1:5000">here</a></strong> and use the credentials provided above to log in.</li>
                <li style="margin-top: 10px; margin-bottom: 20px;">
                    Upon your first login, you will be prompted to change your password. Kindly choose a secure password that is unique and not used for any other accounts.
                </li>
            </ol>
            <p style="color: red;">Please note that this password is only valid for your first login.</p>
            <p>Thanks for using grumPY!</p>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the addressee, do not disclose, copy, circulate, or in any other way use or rely on the information contained in this email or any attachments. 
                If received in error, please delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """
    # Send the email
    mail.send(msg)

def send_virus_liability_email(recipient_email, recipient_name):
    # Create a Message object with the subject, sender and recipient
    msg = Message('grumPY Virus Liability Disclaimer', sender='flask.grumpy@gmail.com', recipients=[recipient_email])
    # Add the message body
    msg.html = f"""
    <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>Welcome to grumPY!</p>
            <p>
                As part of our commitment to your security, we would like to remind you about the potential risks associated with email communications. 
                Please review the following disclaimer regarding the unintentional transmission of computer viruses.
            </p>
            <p style="font-weight: bold;">Disclaimer of Liability for Viruses</p>
            <p>
                grumPY takes reasonable measures to ensure that our systems and communications are free from viruses, malware, or other harmful components. 
                However despite our best efforts, we cannot guarantee that our emails, files, or communications are entirely free from viruses or other potentially harmful elements.
            </p>
            <p style="color: red;">By using this website to receive or access any content, communication, or files from grumPY, you acknowledge and agree to the following:</p>
            <ol style="margin-top: 10px; margin-bottom: 10px;">
                <li style="margin-bottom: 10px;">
                    <strong>No Warranty</strong>: grumPY makes no warranties, representations, or guarantees that any files, emails, or other communications received from us are free of viruses, malware, or other harmful components.
                </li>
                <li style="margin-bottom: 10px;">
                    <strong>No Liability</strong>: grumPY will not be liable for any loss, damage, or disruption caused by the transmission of viruses, malware, or other harmful elements, whether intentionally or unintentionally, through our communications or systems.
                </li>
                <li style="margin-bottom: 10px;">
                    <strong>User Responsibility</strong>: It is the responsibility of the recipient to ensure that their own systems are adequately protected against viruses, malware, and other potential threats. 
                    We strongly recommend that you employ appropriate security measures, including up-to-date antivirus software and regular system scans.
                </li>
                <li style="margin-bottom: 10px;">
                    <strong>Indemnification</strong>: By receiving or accessing content from grumPY, you agree to indemnify and hold grumPY harmless from any claims, losses, or damages arising out of or related to the transmission of viruses or other harmful elements.
                </li>
            </ol>
            <p>Thank you for your attention to this important matter.</p>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the addressee, do not disclose, copy, circulate, or in any other way use or rely on the information contained in this email or any attachments. 
                If received in error, please delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """
    # Send the email
    mail.send(msg)

def send_deactivation_warning_email(recipient_email, recipient_name, recipient_deactivation_time):
    # Create a Message object with the subject, sender, and recipient
    msg = Message('[URGENT] Account Deactivation Notice', sender='flask.grumpy@gmail.com', recipients=[recipient_email])

    #Convert timestamp to readable time
    timestamp = recipient_deactivation_time.strftime('%d/%m/%y %H:%M:%S')

    # Add the message body
    msg.html = f"""
    <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>
                We regret to inform you that your account on the grumPY system will be deactivated in 5 minutes. 
                This decision was made due to some issues with emergency server maintainence.
            </p>
            <p>
                We apologize for any inconvenience this may cause. Please ensure that any necessary actions or data retrievals are completed before your account is deactivated.
                If you believe this deactivation is in error or have any concerns, please contact our support team immediately.
            </p>
            <p>
                We appreciate your understanding and cooperation.
            </p>
            <p style="font-weight: bold;">Account Deactivation</p>
            <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td>User Name</td>
                    <td><strong>{recipient_name}</strong></td>
                </tr>
                <tr>
                    <td>Email Address</td>
                    <td><strong>{recipient_email}</strong></td>
                </tr>
                <tr>
                    <td>Deactivation Time</td>
                    <td><strong>{timestamp}</strong></td>
                </tr>
            </table>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY Team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the intended recipient, please do not disclose, copy, circulate, or otherwise use the information contained in this email or any attachments. 
                If received in error, kindly delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """
    
    # Send the email
    mail.send(msg)

def send_reactivation_warning_email(recipient_email, recipient_name):
    # Create a Message object with the subject, sender, and recipient
    msg = Message('[IMPORTANT] Account Reactivation Notice', sender='flask.grumpy@gmail.com', recipients=[recipient_email])
    
    # Add the message body
    msg.html = f"""
    <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>
                We are pleased to inform you that your account on the grumPY system has been reactivated. 
                You can now log in and access all the features and services as usual.
            </p>
            <p>
                We apologize for any inconvenience caused during the deactivation period. If you encounter any issues or have any concerns, 
                please don't hesitate to contact our support team.
            </p>
            <p>
                Thank you for your continued support and cooperation.
            </p>
            <p style="font-weight: bold;">Account Reactivation Details</p>
            <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <td>User Name</td>
                    <td><strong>{recipient_name}</strong></td>
                </tr>
                <tr>
                    <td>Email Address</td>
                    <td><strong>{recipient_email}</strong></td>
                </tr>
            </table>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY Team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the intended recipient, please do not disclose, copy, circulate, or otherwise use the information contained in this email or any attachments. 
                If received in error, kindly delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """
    
    # Send the email
    mail.send(msg)

def send_forget_password_unsuccessful_email(recipient_name, recipient_email):
    # Create a Message object with the subject, sender, and recipient
    msg = Message('Unsuccessful Forget Password Request', sender='flask.grumpy@gmail.com', recipients=[recipient_email])
    
    # Add the message body
    msg.html = f"""
    <html>
        <body>
            <p>Dear {recipient_name},</p>
            <p>
                We would like to remind you that we previously sent you an email containing your temporary login credentials for your account setup. 
                If you have not already done so, please check your inbox (and spam/junk folder) for this email and use the provided credentials to log in for the first time.
            </p>
            <p style="color: red;">
                Please note that the 'Reset Password' option will be available once you have completed your initial login.
            </p>
            <p>Thank you for your attention to this matter.</p>
            <p style="margin-top: 30px;">Best regards,<br>The grumPY Team</p>
            <hr>
            <p style="color: grey; font-size: smaller;">
                Note: This email and any attachments are confidential and may also be privileged. 
                If you are not the intended recipient, please do not disclose, copy, circulate, or otherwise use the information contained in this email or any attachments. 
                If received in error, kindly delete this email and any attachments from your system.
            </p>
            <p style="color: grey; font-size: smaller; font-style: italic;">
                This is an auto-generated email; please do not reply.
            </p>
        </body>
    </html>
    """
    
    # Send the email
    mail.send(msg)
