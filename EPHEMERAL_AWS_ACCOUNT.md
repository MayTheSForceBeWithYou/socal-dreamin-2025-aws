# Ephemeral AWS Account Setup & Teardown Guide

This guide explains how to create a **temporary AWS account** (with free-tier benefits) using a disposable email, use it for a short-term lab or workshop, and then safely tear everything down when finished.

---

## 1. Create a Free Email Account
- Sign up for a new Gmail, Outlook, or Proton Mail account.
  - Example: `socal.dreamin.2025.<yourname>@gmail.com`
- Use a password you don’t mind throwing away.
- Save login info in a safe place (password manager or text file).
- This email will be used only for AWS sign-up and can be deleted later.

---

## 2. Create a Net-New AWS Account
- Go to [AWS Free Tier](https://aws.amazon.com/free/) → **Create a Free Account**.
- Use your new email address.
- Provide personal details (name, address, phone — can match your real info).
- Add a **credit/debit card** (required for identity verification).  
  - Tip: use a **virtual card** with a low spending cap for extra safety.
- Select **Basic Support Plan** (free).
- Verify phone and email to finish signup.
- Log in as the root user and enable **MFA** on the root account.

---

## 3. Do the Workshop Work
- Use this AWS account to spin up:
  - S3 bucket(s)
  - Kinesis Firehose
  - Amazon OpenSearch Service domain
  - IAM users/roles
  - Optional: EC2 instance in a foreign region to simulate international logins
- Remember: all services are eligible for free tier in the **first 12 months** of account creation, but you only need the account for the workshop window.

---

## 4. Tear Down the AWS Account
When the workshop or lab is finished:
- Delete all AWS resources (OpenSearch domain, Firehose, S3, EC2, IAM, etc.).
- Confirm billing shows **$0.00**.
- Go to **Account Settings → Close Account** while signed in as root.
- AWS will retain data for 90 days, then fully delete.

---

## 5. Tear Down the Email Account
- Once AWS account is closed and confirmed, log in to your Gmail/Outlook/Proton settings.
- Delete the email account entirely.
- This ensures both AWS and the associated identity are disposed of.

---

## Pro Tips
- Set up an **AWS Budget alarm** ($5 threshold) for peace of mind.
- Keep a temporary record of AWS and email credentials until teardown day.
- If repeating this often, consider AWS Organizations to manage disposable sub-accounts.

---

## Disclaimer

This workshop uses **free-tier resources** from AWS and free email services (e.g., Gmail) to demonstrate real-world security monitoring concepts at zero cost.  

- Creating a new Gmail (or similar) account for this workshop is permitted by Google’s Terms of Service, provided the account is not used for spam, abuse, or impersonation.  
- Creating a new AWS account to access free-tier benefits is permitted by AWS’s Terms of Service. However, **abusing the free tier by systematically creating multiple accounts to avoid paying for services is not allowed**.  
- All attendees are expected to:
  - Use free-tier resources responsibly.  
  - Tear down all AWS resources after the workshop.  
  - Close temporary AWS/email accounts if no longer needed.  

Neither the presenter nor this workshop is affiliated with or endorsed by AWS, Salesforce, Google, or any other provider. **Attendees are responsible for their own usage and compliance with provider Terms of Service.**

---

**End of Guide**
