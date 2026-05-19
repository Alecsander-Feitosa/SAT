import re

file_path = "c:/Users/Micro/Desktop/venv/SAT/accounts/views.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

def replacer(match):
    domain = match.group(1)
    filename = match.group(2)
    if domain == "commons":
        return f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}"
    else:
        return f"https://pt.wikipedia.org/wiki/Special:FilePath/{filename}"

# The regex matches the Wikipedia upload URL pattern
new_content = re.sub(r'https://upload\.wikimedia\.org/wikipedia/(commons|pt)/[a-f0-9]/[a-f0-9]{2}/([^"]+)', replacer, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Done replacing URLs.")
