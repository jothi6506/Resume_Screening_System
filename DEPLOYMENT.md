# Deployment Guide - Cloud-Based AI-Powered Resume Screening & Recruitment System

This document outlines the architecture, centralized cloud database setup, cloud object storage integration, production WSGI deployment, and environment variable configuration for the **Cloud-Based AI-Powered Resume Screening and Recruitment System**.

---

## 1. Cloud Architecture Overview

```
                           HR & Recruiter Users
                                    │
                                    ▼ (HTTPS / Internet)
                     ┌──────────────────────────────┐
                     │ Cloud Flask Web Application  │
                     │  (Gunicorn WSGI + WhiteNoise)│
                     └──────────────┬───────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Cloud Database  │      │  Cloud Storage   │      │   AI Services    │
│ (Centralized     │      │ (AWS S3 /        │      │ (ATS Engine &    │
│  Cloud MySQL)    │      │  Cloudinary)     │      │  Recruitment AI) │
└──────────────────┘      └──────────────────┘      └──────────────────┘
```

---

## 2. Centralized Cloud Database Setup

The production application requires a centralized cloud-hosted MySQL database so multiple HR users across different locations access the same single source of truth.

### Recommended Cloud MySQL Providers:
- **TiDB Cloud** (Free MySQL Compatible Serverless)
- **Aiven for MySQL** (Free-Tier Cloud MySQL)
- **Railway MySQL** (1-Click Cloud MySQL)
- **AWS RDS for MySQL**

### Database Migration & Setup Steps:
1. Provision a Cloud MySQL instance on your chosen cloud database provider.
2. Obtain your Cloud MySQL connection URI. Format:
   ```
   mysql+pymysql://<user>:<password>@<cloud-db-host>:3306/<database_name>
   ```
3. Set the `DATABASE_URL` environment variable in your cloud web hosting dashboard.
4. Apply migrations to initialize schema on the cloud database:
   ```bash
   flask db upgrade
   ```
5. Seed initial admin account:
   ```bash
   flask seed
   ```

---

## 3. Real Cloud Resume Storage Setup

Resume files are managed via a storage service abstraction supporting both local disk storage and cloud object storage.

### Option A: AWS S3 Object Storage
1. Create an AWS S3 Bucket (e.g. `my-resume-screening-bucket`).
2. Generate an IAM user with `AmazonS3FullAccess` or a bucket policy allowing `s3:PutObject`, `s3:GetObject`, and `s3:DeleteObject`.
3. Set the following environment variables in your cloud deployment platform:
   ```env
   STORAGE_TYPE=s3
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_STORAGE_BUCKET_NAME=my-resume-screening-bucket
   AWS_REGION=us-east-1
   ```

### Option B: Cloudinary Storage
1. Sign up for a free Cloudinary account.
2. Copy your `CLOUDINARY_URL` from the Cloudinary Dashboard.
3. Set the environment variables:
   ```env
   STORAGE_TYPE=cloudinary
   CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
   ```

---

## 4. Cloud Web Application Hosting Setup

The application is configured to run using **Gunicorn** WSGI production server and **WhiteNoise** for static assets.

### Deploying to Render.com (1-Click Deploy):
1. Push repository to GitHub.
2. Log into [Render.com](https://render.com) and click **New + -> Web Service**.
3. Connect your GitHub repository.
4. Render will automatically detect `render.yaml` or set the following details:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn run:app`
5. Under **Environment Variables**, add:
   - `FLASK_APP` = `run.py`
   - `FLASK_ENV` = `production`
   - `SECRET_KEY` = `<random-long-secret-key>`
   - `DATABASE_URL` = `<your-cloud-mysql-connection-url>`
   - `STORAGE_TYPE` = `s3` (or `cloudinary` / `local`)
6. Click **Deploy Web Service**. You will receive a public HTTPS URL (e.g. `https://resume-screening-system.onrender.com`).

---

## 5. Environment Variables Reference

| Variable Name | Description | Example / Default |
|---|---|---|
| `FLASK_APP` | Entry point script | `run.py` |
| `FLASK_ENV` | App environment (`development` or `production`) | `production` |
| `SECRET_KEY` | Flask session secret key | `super-secret-key` |
| `DATABASE_URL` | Cloud MySQL connection string | `mysql+pymysql://user:pass@host:3306/db` |
| `STORAGE_TYPE` | Storage backend (`local`, `s3`, `cloudinary`) | `s3` |
| `AWS_ACCESS_KEY_ID` | AWS IAM access key ID | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret access key | `secret...` |
| `AWS_STORAGE_BUCKET_NAME` | S3 Bucket name for resumes | `resume-bucket` |
| `AWS_REGION` | AWS S3 region | `us-east-1` |
| `CLOUDINARY_URL` | Cloudinary API connection URI | `cloudinary://key:secret@name` |
| `MAIL_SERVER` | SMTP host for email notifications | `smtp.gmail.com` |
| `MAIL_PORT` | SMTP port | `465` |
| `MAIL_USERNAME` | HR Sender Email | `hr@company.com` |
| `MAIL_PASSWORD` | SMTP App Password | `app-password` |

---

## 6. Multi-User Centralized System Access

Once deployed to a cloud hosting platform:
- HR recruiters access the application via any web browser on desktop, tablet, or mobile using the public HTTPS URL.
- All HR actions (job posts, candidate status updates, resume uploads, email notifications, interview evaluations) sync instantaneously across all users via the Centralized Cloud Database.

---

## 7. Real-Time System & Cloud Status Monitoring

To verify cloud services are properly connected and operational:
1. Log into the system as an HR user.
2. Navigate to **System Status** in the sidebar (or visit `/system/status`).
3. The page performs live runtime checks against:
   - **Centralized Database**: Verifies live connection, database host, dialect, and record counts.
   - **Cloud Object Storage**: Verifies storage health, active driver mode (`s3`, `cloudinary`, or `local`), and bucket access.
   - **Environment & WSGI Server**: Confirms `production` mode and Gunicorn WSGI execution.
