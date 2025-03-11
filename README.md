# DJI2Lz - A Lightweight HUD Generator for DJI Drone 

## Features

- **GPS Coordinates**
- **Altitude Bar**
- **Altitude Counter**
- **Photo EXIF Integration**
- **Custom Text for Filter Lens** in `LayoutConfig.py`
- **Distance from Operator**
- **Total distance** 
- **Horizontal Speedometer** with text in m/s and km/h
- **Vertical Speedometer** with text in m/s and km/h
- **Satellite Counter** with colored text based on satellite status
- **Flight path maps** auto scale based on the area covered


![Sample HUD Output](/DJISAMPLE/01.jpg)

![Sample HUD Output](/DJISAMPLE/03.jpg)



## Installation

```bash
git clone https://github.com/JrVolt/DJI2Lz.git

cd DJI2Lz

pip install -r requirements.txt

# Configure a valid font in `LayoutConfig.py` before running

python3 DJI2Lz_Launcher.py
```
## Usage

For long shoot/flight, divided in `multiple DJI.mp4` please follow this process, for correct GPS drawing.

1. Extract all the .srt from the videos `DJI_0001.mp4 DJI_0002.mp4 DJI_0003.mp4`
2. Merge the extracted file, `Launcher option 5`
3. Generate the HUD forom `DJI_MERGED_0001-0002-0003.srt` 

## Editing 

The script will export a lots of trasparent .png in UHD resolution (3840x2160)
In you preferred video editor make sure to strech each to cover 1 ses of video, based on your timeline's frame rate.

(IE: Video@25p each .png shuld last 25 frames.)


### External Dependencies

This project uses an executable from another open-source project named `dji-log-parser` by `lvauvillier` . The binary is provided along with the files for user convenience. However, you must obtain and add a valid DJI API key to decode the flight log.

API Setup:
1. Rename `SAMPLE_DJI_API_KEY.py` in `DJI_API_KEY.py` 
2. Edit the file with a valid key


## Platform Compatibility

- **Linux/Unix:** Fully supported.
- **Mac:** Should work at 99% with minor fixes. (brew maybe ?)
- **Windows WSL:** May work, but troubleshooting will likely be required.
- **Windows (Native):** Not supported. Feel free to fork and add support for Windows.

### Drone Compatibility

It suppsed to be compatible to every DJI drone that support the telemetry in subtile track. 
Some older drone or firmware (maybe both) have a separate .srt along the .mp4 file. 

## Configuration

### Basic

All visual elements can be customized through constants in `LayoutConfig.py`. These include:
- **Resolution** If edited instrruments repositioning is required. (Preset UHD downscale if needed) 
- **Text Color**
- **Font Details**

Each instrument can be individually enabled or disabled with ease with a simple list of `True/False` option. 

### Altitude and Speed Limits
- **Altitude Limits:** Easily configure minimum and maximum altitude values.
- **Speed Limits:** Customizable, but altering these values might break the speedometer drawing. Proceed with caution.

### Text Positioning
All text positioning is configured in the `DJI2Lz-HUD_Generator.py` module. Pay close attention when making changes.
(Is way easier do it in your preferred video editor software)


### Dependencies

- **Pillow (PIL)**
- **matplotlib**
- **numpy**

## Note 
Each modules can be executed standalone, execpt for the flightrecord decode that require `dji-log`, PLEASE DO NOT, they are safer to use with the launcher.

All the goal of the project has already been achieved, it can be considered complete.

Eventually all minor update.

### Contributing

1. Fork the repository.
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.