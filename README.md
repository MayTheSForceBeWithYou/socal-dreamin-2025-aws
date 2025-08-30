# Salesforce → AWS → OpenSearch Security Lab

This repository contains workshop materials for **SoCal Dreamin'** on
building a free-tier, real-time monitoring pipeline for Salesforce login
activity using AWS and OpenSearch.

## Overview

We will set up a lab environment where Salesforce activity logs (e.g.,
`LoginHistory`) are ingested into AWS, streamed through **Kinesis Data
Firehose**, and indexed in **Amazon OpenSearch Service** for
visualization, anomaly detection, and security alerting.

**Architecture Flow:**

    Salesforce (LoginHistory / API)
          ↓
    Python Script / Lambda (middleware)
          ↓
    Kinesis Data Firehose → S3 backup
          ↓
    Amazon OpenSearch Service
          ↓
    OpenSearch Dashboards (alerts, anomaly detection, visualizations)

## Prerequisites

-   Salesforce Developer Edition OR Trailhead Playground OR Scratch Org
-   AWS account (free tier eligible)
-   Python 3.9+
-   AWS CLI configured (`aws configure`)
-   Basic knowledge of Salesforce & AWS

## Manual Walkthrough (Summary)

1.  **Salesforce Setup**
    -   Create a Developer Org, Trailhead Playground, or Scratch Org.
    -   Collect `LoginHistory` events via Salesforce APIs.
    -   Generate a Security Token for API access.
2.  **AWS Setup**
    -   Create S3 bucket (backup destination).
    -   Create an **Amazon OpenSearch Service** domain
        (`t3.small.search`, free tier).
    -   Create a **Kinesis Firehose** delivery stream → OpenSearch (+ S3
        backup).
3.  **Local Ingestion Script**
    -   Use Python + `simple-salesforce` + `boto3` to pull LoginHistory
        from Salesforce and push to Firehose.
    -   Example script included in `/scripts/ingest_login_history.py`.
4.  **Visualize in OpenSearch**
    -   Create index template (`sfdc-logins*`).
    -   Build dashboards to monitor:
        -   Failed logins by time
        -   Top source IPs (failures)
        -   Suspicious login geolocations
    -   (Optional) Enable Anomaly Detection & Alerting.
5.  **Optional EC2 Instance**
    -   Launch an EC2 instance in a **non-US region** with Salesforce
        CLI installed.
    -   Use it to log in to Salesforce to simulate foreign logins →
        validate anomaly detection.

## Future Work

We will later evolve this lab into **Infrastructure as Code (IaC)**
with: - Salesforce Scratch Org setup (Config JSON). - AWS Terraform
configurations (JSON). - Automated Lambda ingestion instead of local
scripts.

## Workshop Goals

-   Show Salesforce professionals how to extend org security monitoring
    using **cloud-native and open-source tools**.
-   Provide a free-tier, hands-on SIEM-like experience without requiring
    Splunk licenses.
-   Teach reusable patterns for integrating Salesforce into enterprise
    security ecosystems.

## License

MIT License
