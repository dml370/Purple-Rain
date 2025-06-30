# AI Companion - Oracle Cloud Deployment Guide

This guide provides the necessary steps to configure your OCI environment to run the AI Companion platform.

## 1. Networking Setup
- **VCN:** Ensure you have a Virtual Cloud Network (VCN) set up.
- **Security List / Ingress Rules:** In your VCN's security list, you must add Ingress Rules to allow traffic on the ports used by the application:
  - **Port 8000 (TCP):** For the production application running via Gunicorn.
  - **Port 443 (TCP):** If you are setting up an SSL/TLS terminator on a load balancer.
  - Source for both should be `0.0.0.0/0`.

## 2. Oracle Autonomous Database (ADB)
1.  **Provision ADB:** Create an Oracle Autonomous Database instance (ATP or ADW).
2.  **Download Wallet:** Go to the database's details page, click "DB Connection," and download the Client Credentials (Wallet). This will be a `.zip` file.
3.  **Wallet Password:** When downloading, you will be prompted to create a password for the wallet. Remember this password.
4.  **Configuration:** You will need to place the unzipped wallet files in a secure location on your server and provide the path and password in your `.env` file for the application to connect.

## 3. Object Storage
1.  **Create a Bucket:** In the OCI console, navigate to Object Storage and create a new private bucket. This will be used for storing user-uploaded files, artifacts, etc.
2.  **Credentials:** The application will use the instance principal credentials to interact with this bucket, so no extra keys are needed if running on an OCI compute instance.

## 4. Load Balancer (Recommended for Production)
- When setting up a public-facing Load Balancer, ensure it is configured to support **WebSockets**. This usually involves setting longer connection timeouts and ensuring the backend health check is pointing to the `/health/detailed` endpoint.
