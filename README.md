# DJI2Lz - A Lightweight HUD Generator for DJI Drone 

## Features

- **GPS Coordinates**
- **Altitude Bar**
- **Altitude Counter**
- **Photo EXIF Integration**
- **Custom Text for Filter Lens**
- **Distance from Operator**
- **Horizontal Speedometer** with text in m/s and km/h
- **Vertical Speedometer** with text in m/s and km/h
- **Satellite Counter** with colored text based on satellite status


![Sample HUD Output](/DJISAMPLE/01.jpg)

![Sample HUD Output](/DJISAMPLE/02.jpg)



## Installation

```bash
git clone https://github.com/JrVolt/DJI2Lz.git

cd DJI2Lz

pip install -r requirements.txt

# Configure a valid font in `LayoutConfig.py` before running

python3 DJI2Lz_Launcher.py
```

### External Dependencies

This project uses an executable from another open-source project named `dji-log-parser` by `lvauvillier` . The binary is provided along with the files for user convenience. However, you must obtain and add a valid DJI API key to decode the flight log.

# Platform Compatibility

- **Linux/Unix:** Fully supported.
- **Mac:** Should work at 99% with minor fixes.
- **Windows WSL:** May work, but troubleshooting will likely be required.
- **Windows (Native):** Not supported. Feel free to fork and add support for Windows.

## Configuration

### Basic

All visual elements can be customized through constants in `LayoutConfig.py`. These include:
- **Resolution**
- **Text Color**
- **Font Details**

### Instrument Management
Each instrument can be individually enabled or disabled with ease.

### Altitude and Speed Limits
- **Altitude Limits:** Easily configure minimum and maximum altitude values.
- **Speed Limits:** Customizable, but altering these values might break the speedometer drawing. Proceed with caution.

### Text Positioning
All text positioning is configured in the `DJI2Lz-HUD_Generator.py` module. Pay close attention when making changes.

### Dependencies

- **Pillow (PIL)**
- **matplotlib**
- **numpy**

## Future Development

I plan to continue working on this code and may eventually include:
- **Additional Data from Flight Logs:** Integration of more detailed information from datalog files.
- **Waypoint Map Drawing:** Generate a map from GPS waypoint data (already coded but currently very rough).

These features are not a priority, as the main goal of the project has already been achieved.

### Contributing

1. Fork the repository.
2. Create your feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. Commit your changes:
   ```bash
   git commit -m 'Add some amazing feature'
   ```
4. Push to the branch:
   ```bash
   git push origin feature/amazing-feature
   ```
5. Open a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.