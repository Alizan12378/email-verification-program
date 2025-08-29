import re
import dns.resolver
import smtplib
import threading
from queue import Queue
import csv

INPUT_FILE = "input.txt"
OUTPUT_TXT_FILE = "output.txt"
OUTPUT_CSV_FILE = "output.csv"

# Verify email format
def is_valid_format(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None

# Get MX Records
def get_mx_records(domain):
    try:
        answers = dns.resolver.resolve(domain, 'MX', lifetime=5)
        return [str(r.exchange).rstrip('.') for r in answers]
    except Exception:
        return []

# SMTP verification mailbox availability
def verify_email_smtp(email, mx_records):
    from_address = 'verify@example.com'
    for mx in mx_records:
        try:
            server = smtplib.SMTP(mx, timeout=10)
            server.set_debuglevel(0)
            server.helo()
            server.mail(from_address)
            code, _ = server.rcpt(email)
            server.quit()
            if code == 250:
                return "Valid"
            elif code == 550:
                return "Non-Valid"
        except Exception:
            continue
    return "Could not verify"

# Complete verification process for a single email address
def verify_email(email):
    if not email.strip():
        return "⬜ Blank line"
    if not is_valid_format(email):
        return "Invalid format"
    domain = email.split('@')[1]
    mx_records = get_mx_records(domain)
    if not mx_records:
        return "No MX records"
    return verify_email_smtp(email, mx_records)

# Thread Task Letter
def worker(queue, results, lock):
    while not queue.empty():
        index, email = queue.get()
        status = verify_email(email)
        with lock:
            results[index] = (email, status)
            if email.strip():
                print(f"[{index+1}] {email} → {status}")
            else:
                print(f"[{index+1}] (blank line)")
        queue.task_done()

# Read the mailbox list
def load_emails(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return [line.rstrip('\n') for line in f]

# save output.txt（Each line is status, blank lines are reserved）
def save_status_to_txt(results, output_txt_file):
    with open(output_txt_file, 'w', encoding='utf-8') as f:
        for index in sorted(results.keys()):
            email, status = results[index]
            if not email.strip():
                f.write('\n')
            else:
                f.write(f"{status}\n")

# Only export successfully verified mailboxes
def save_valid_emails_to_csv(results, output_csv_file):
    with open(output_csv_file, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['email address'])  # 首行
        for index in sorted(results.keys()):
            email, status = results[index]
            if email.strip() and status == "Valid":
                writer.writerow([email])

# Batch Verification
def verify_bulk_emails(email_list, num_threads=10):
    queue = Queue()
    results = {}
    lock = threading.Lock()

    for index, email in enumerate(email_list):
        queue.put((index, email))

    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=worker, args=(queue, results, lock))
        t.start()
        threads.append(t)

    queue.join()
    for t in threads:
        t.join()
    return results

# Main program
if __name__ == "__main__":
    try:
        print("🚀 Starting email verification...\n")
        emails = load_emails(INPUT_FILE)
        results = verify_bulk_emails(emails, num_threads=20)
        save_status_to_txt(results, OUTPUT_TXT_FILE)
        save_valid_emails_to_csv(results, OUTPUT_CSV_FILE)
        print(f"\n✅ 已生成 output.txt 及 output.csv！")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    finally:
        input("\n🔚 Press Enter to exit...")
