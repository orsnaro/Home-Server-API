
import pyipp as ipp
import os

# This code uses the 'ipp-client' library.
# Ensure it is installed (e.g., via 'pip install -r requirements.txt')

def send_text_to_printer(printer_ip: str, text_to_print: str) -> tuple[bool, str]:
    """
    Sends a raw string of text to an IPP printer.

    Args:
        printer_ip: The IP address of the printer.
        text_to_print: The string of text to be printed.

    Returns:
        A tuple containing a boolean for success and a status message string.
    """
    # URI for a modern IPP printer. /ipp/print is a common path.
    printer_uri = f"ipp://{printer_ip}:631/ipp/print"

    try:
        # 1. create an IPP client instance
        client = ipp.IPP(printer_uri)

        # 2. send the print job.
        # IPP operation is 'print-job'. We send the text as bytes.
        # also add a form-feed character \f at the end to ensure the page ejects.
        job = client.print_job(
            job_name="Web Print Job",
            data=(text_to_print + "\n\f").encode('utf-8')
        )

        job_id = job.job_id
        message = f"Job sent successfully. Job ID: {job_id}"
        print(message)
        return True, message

    except Exception as e:
        message = f"An error occurred while sending print job: {e}"
        print(message)
        return False, message

