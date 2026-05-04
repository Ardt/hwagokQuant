"""
OCI A1 (Ampere ARM) Instance Auto-Provisioner
Retries LaunchInstance until capacity becomes available.

Prerequisites:
  Python 3.8+ (no manual pip install needed — auto-installs oci SDK)
  Set up OCI config: ~/.oci/config (or use env vars)
  Get values from OCI Console → Compute → Create Instance (inspect the form)

Usage:
  python oci_a1_launcher.py
"""

import subprocess, sys

try:
    import oci
except ImportError:
    print("Installing oci SDK...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "oci==2.133.0", "-q"])
    import oci
import time
import sys
from datetime import datetime

# ===== CONFIGURE THESE =====
COMPARTMENT_ID = "ocid1.tenancy.oc1..YOUR_TENANCY_OCID"
AVAILABILITY_DOMAIN = "xxxx:AP-CHUNCHEON-1-AD-1"  # OCI Console → Compute → AD name
SUBNET_ID = "ocid1.subnet.oc1.ap-chuncheon-1.YOUR_SUBNET_OCID"
IMAGE_ID = "ocid1.image.oc1.ap-chuncheon-1.YOUR_IMAGE_OCID"  # Ubuntu 22.04 ARM
SSH_PUBLIC_KEY_PATH = "~/.ssh/id_rsa.pub"

# A1 Free Tier: up to 4 OCPUs, 24GB RAM (total across all A1 instances)
INSTANCE_NAME = "quant-a1"
OCPUS = 4
MEMORY_GB = 24

# Retry settings
RETRY_INTERVAL_SEC = 60  # check every 60 seconds
MAX_RETRIES = 0  # 0 = infinite
# ===========================


def launch():
    config = oci.config.from_file()
    compute = oci.core.ComputeClient(config)

    with open(SSH_PUBLIC_KEY_PATH.replace("~", str(__import__("pathlib").Path.home()))) as f:
        ssh_key = f.read().strip()

    launch_details = oci.core.models.LaunchInstanceDetails(
        compartment_id=COMPARTMENT_ID,
        availability_domain=AVAILABILITY_DOMAIN,
        display_name=INSTANCE_NAME,
        shape="VM.Standard.A1.Flex",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=OCPUS,
            memory_in_gbs=MEMORY_GB,
        ),
        source_details=oci.core.models.InstanceSourceViaImageDetails(
            source_type="image",
            image_id=IMAGE_ID,
            boot_volume_size_in_gbs=50,
        ),
        create_vnet_details=None,
        metadata={"ssh_authorized_keys": ssh_key},
        subnet_id=SUBNET_ID,
    )

    attempt = 0
    while True:
        attempt += 1
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] Attempt #{attempt}...", end=" ")

        try:
            response = compute.launch_instance(launch_details)
            instance = response.data
            print(f"\n✅ SUCCESS! Instance OCID: {instance.id}")
            print(f"   Name: {instance.display_name}")
            print(f"   State: {instance.lifecycle_state}")
            print(f"   Shape: {instance.shape} ({OCPUS} OCPU, {MEMORY_GB}GB)")
            return instance
        except oci.exceptions.ServiceError as e:
            if e.status == 500 and "Out of host capacity" in str(e.message):
                print(f"Out of capacity. Retrying in {RETRY_INTERVAL_SEC}s...")
            elif e.status == 500 and "InternalError" in str(e.code):
                print(f"Internal error. Retrying in {RETRY_INTERVAL_SEC}s...")
            elif e.status == 429:
                print(f"Rate limited. Retrying in {RETRY_INTERVAL_SEC * 2}s...")
                time.sleep(RETRY_INTERVAL_SEC)
            else:
                print(f"\n❌ Unexpected error: {e.status} {e.code} - {e.message}")
                sys.exit(1)

        if MAX_RETRIES and attempt >= MAX_RETRIES:
            print(f"\n❌ Gave up after {MAX_RETRIES} attempts.")
            sys.exit(1)

        time.sleep(RETRY_INTERVAL_SEC)


if __name__ == "__main__":
    print("OCI A1 Auto-Provisioner")
    print(f"Target: {OCPUS} OCPU / {MEMORY_GB}GB RAM")
    print(f"Retry interval: {RETRY_INTERVAL_SEC}s")
    print("-" * 40)
    launch()
