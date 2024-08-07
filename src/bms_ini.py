class FalconBMSIni:
    def __init__(self, file_path):
        self.file_path = file_path
        self.sections = {}

    def load(self):
        with open(self.file_path, 'r') as file:
            current_section = None
            for line in file:
                line = line.strip()
                if line.startswith('[') and line.endswith(']'):
                    section_name = line[1:-1]
                    current_section = section_name
                    self.sections[section_name] = {}
                elif '=' in line:
                    key, value = line.split('=', 1)
                    if current_section:
                        self.sections[current_section][key.strip()] = value.strip()

    def get_section(self, section_name):
        return self.sections.get(section_name, {})

    def get_value(self, section_name, key):
        section = self.get_section(section_name)
        return section.get(key)

    def set_value(self, section_name, key, value):
        section = self.sections.setdefault(section_name, {})
        section[key] = value

    def save(self):
        with open(self.file_path, 'w') as file:
            for section_name, section in self.sections.items():
                file.write(f'[{section_name}]\n')
                for key, value in section.items():
                    file.write(f'{key}={value}\n')
                file.write('\n')