import os

basedir = os.path.abspath(os.path.dirname(__file__))


pcr_ssh_ip = os.getenv("PCR_SSH_IP")
pcr_ssh_user = os.getenv("PCR_SSH_USER")
pcr_ssh_pass = os.getenv("PCR_SSH_PASS")
pcr_ssh_url = os.getenv("PCR_SSH_URL")
pcr_db_name = os.getenv("PCR_DB_NAME")
pcr_db_conn_str = os.getenv("PCR_DB_CONN_STR")
auth_user = os.getenv("AUTH_USER")
auth_pass = os.getenv("AUTH_PASS")
auth_pair = {auth_user:auth_pass}
