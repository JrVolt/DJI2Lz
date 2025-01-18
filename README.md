## Features

- GPS Coordinate
- Altitude bar
- Altitude counter
- Photo EXIF 
- Custom text for filter lens
- Distance from Operator
- Horizontal speedometer with text in m/s and km/s
- Vertical speedometer with text in m/s and km/s
- Satellite counter with colored text based on satellite.

## Installation

git clone https://github.com/JrVolt/DJI2Lz.git
cd DJI2Lz 

pip install -r requirements.txt

YOU MUST CONFIGURE A VALID FONT IN LayoutConfig.py
(unless )
python3 DJI2Lz.py

# Install dependencies



## Basic configuration

All visual elements can be configured through constants in `LayoutConfig.py` like resolution, text color, font details.
Each instruments can be individually enable easily.

Is possible to easly configure altitude min and max limit. 
Is also possible to chang the speed limit.
    KEEP IN MIND THAT CHANGING THIS WILL PROBLY BROKE THE SPEEDOMETER DRAW.

All the text positioning is configured in the DJI2Lz-HUD_Generator.py module, PAY ATTENTION


## Dependencies

- PIL (Pillow)
- matplotlib
- numpy

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by standard aviation attitude indicators
- Developed for drone interface applications
