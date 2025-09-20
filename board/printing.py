# =============================================
# File: printing.py
# Version: 1.0.1-Beta
# Author: Omar Rashad
# Python Version: 3.13.1 (tags/v3.13.1:0671451, Dec  3 2024, 19:06:28) [MSC v.1942 64 bit (AMD64)]
# Last Update: 2025-05-22
# =============================================
import cups
import os

import time

IPP_JOB_COMPLETED = 9

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

        while conn.getJobAttributes(job_id)['job-state'] != IPP_JOB_COMPLETED:
            time.sleep(1)

        message = f"Job sent successfully. Job ID: {job_id}"
        print(message)
        return True, message

    except Exception as e:
        message = f"An error occurred while sending print job: {e}"
        print(message)
        return False, message


