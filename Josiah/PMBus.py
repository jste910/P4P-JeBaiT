start_line = 225338
end_line = 269644
with open("log.txt", "r") as source, open("i.txt", "w") as dest:
    # enumerate(..., 1) makes the line count start at 1 instead of 0
    for line_num, line in enumerate(source, 1):
        if start_line <= line_num <= end_line:
            dest.write(line)
        elif line_num > end_line:
            break  # Stop reading the file early to save time