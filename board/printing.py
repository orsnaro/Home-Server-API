# =============================================
# File: printing.py
# Version: 1.0.2-Beta
# Author: Omar Rashad
# Python Version: 3.13.1 (tags/v3.13.1:0671451, Dec  3 2024, 19:06:28) [MSC v.1942 64 bit (AMD64)]
# Last Update: 2025-10-21
# =============================================
import cups
import os
from threading import Thread
import time

IPP_JOB_COMPLETED = 9
IPP_JOB_ABORTED = 8
IPP_JOB_CANCELED = 7
IPP_JOB_STOPPED = 6
IPP_JOB_HELD = 4 #most of  the time it's done and waiting for release!
IPP_JOB_PENDING= 3 #not started yet

def print_job_state_notifier(conn, job_id):
    job_state = IPP_JOB_PENDING 
    while  job_state not in [IPP_JOB_COMPLETED, IPP_JOB_HELD]:
        job_state =  conn.getJobAttributes(job_id)['job-state']
        print(f"\033[33m info: Current Print job  State: {job_state}\033[0m")
        
        if job_state in [IPP_JOB_ABORTED, IPP_JOB_CANCELED, IPP_JOB_STOPPED] :
            break #failed no need to wait further
        else :    
            time.sleep(1)

    if job_state in [IPP_JOB_COMPLETED, IPP_JOB_HELD] :
        print(f"\033[32mOK: Print Job Completed Successfuly!\033[0m")
    else: 
        print(f"\033[30mERROR: couldn't complete print job!\033[0m")
        
def print_file(file_path: str) -> tuple[bool, str]:
    """
    Sends a raw string of text to an IPP printer.

    Args:
        text_to_print: The string of text to be printed.

    Returns:
        A tuple containing a boolean for success and a status message string.
    """
    try:
        conn = cups.Connection()

        printers = conn.getPrinters()
        if not printers:
            return False, "No printers found."

        printer_name = list(printers.keys())[0]

        job_id = conn.printFile(printer_name, file_path, "Web Print Job", {})
        
        Thread(target=print_job_state_notifier, args=(conn, job_id)).start() # non-blocking  job status checking loop
        
        return True, "Found a printer ... sent a print job!"

    except Exception as e:
        message = f"An error occurred while sending print job: {e}"
        print(f"\033[30m{message}\033[0m")
        return False, message


