
import cups
import os

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

        message = f"Job sent successfully. Job ID: {job_id}"
        print(message)
        return True, message

    except Exception as e:
        message = f"An error occurred while sending print job: {e}"
        print(message)
        return False, message


