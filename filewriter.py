def add_guild_data(guild, file, data=None):
    guild = str(guild)
    try:
        with open(file + ".txt", "a") as f:
            if str(data) is not None:
                f.write(guild + "," + str(data) + "\n")
            else:
                f.write(guild)
        return True
    except:
        return False

def get_guild_data(guild, file):
    guild = str(guild)
    try:
        with open(file + ".txt", "r") as f:
            for line in f:
                if line.startswith(guild):
                    if "," not in line:
                        return True
                    return line.split(",")[1].strip()
    except:
        return None

def remove_guild_data(guild, file):
    guild = str(guild)
    try:
        with open(file + ".txt", "r") as f:
            lines = f.readlines()
        with open(file + ".txt", "w") as f:
            for line in lines:
                if not line.startswith(guild):
                    f.write(line)
        return True
    except:
        return False