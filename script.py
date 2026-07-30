import os

# Number of files to create
n = int(input("Enter the number of files to create: "))

# Output folder
output_dir = "C:\\Users\\Lenovo\\Documents\\Project\\QUIC\\output"
os.makedirs(output_dir, exist_ok=True)

# Create n text files
for i in range(1, n + 1):
    file_path = os.path.join(output_dir, f"file_{i}.txt")
    with open(file_path, "w") as f:
        f.write(f"This is sample file {i}.\n")

print(f"{n} text files created successfully in the '{output_dir}' folder.")