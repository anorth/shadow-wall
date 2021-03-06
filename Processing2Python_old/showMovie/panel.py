from helperFunctions import percentage

# def send_frame_to_led_panels(frame, num_ports, led_area, led_image, led_data, led_layout):
#    #Write the frame to panels
#    for i in range(0, num_ports):
#      #copy a portion of the movie's image to the LED image
#      xoffset = percentage(frame.width, led_area[i].x)
#      yoffset = percentage(frame.height, led_area[i].y)
#      xwidth =  percentage(frame.width, led_area[i].width)
#      yheight = percentage(frame.height, led_area[i].height)
#
#      led_image[i].copy(frame, xoffset, yoffset, xwidth, yheight, 0, 0, led_image[i].width, led_image[i].height)
# #     // convert the LED image to raw data
# #     byte[] ledData =  new byte[(ledImage[i].width * ledImage[i].height * 3) + 3];
# #     image2data(ledImage[i], ledData, ledLayout[i]);
# #     if (i == 0) {
# #       ledData[0] = '*';  // first Teensy is the frame sync master
# #       int usec = (int)((1000000.0 / TargetFrameRate) * 0.75);
# #       ledData[1] = (byte)(usec);   // request the frame sync pulse
# #       ledData[2] = (byte)(usec >> 8); // at 75% of the frame time
# #     } else {
# #       ledData[0] = '%';  // others sync to the master board
# #       ledData[1] = 0;
# #       ledData[2] = 0;
# #     }
# #     // send the raw data to the LEDs  :-)
# #     ledSerial[i].write(ledData);
# #   }
# # }
# #


# // image2data converts an image to OctoWS2811's raw data format.
# // The number of vertical pixels in the image must be a multiple
# // of 8.  The data array must be the proper size for the image.
# void image2data(PImage image, byte[] data, boolean layout) {
#   int offset = 3;
#   int x, y, xbegin, xend, xinc, mask;
#   int linesPerPin = image.height / 8;
#   int pixel[] = new int[8];
#
#   for (y = 0; y < linesPerPin; y++) {
#     if ((y & 1) == (layout ? 0 : 1)) {
#       // even numbered rows are left to right
#       xbegin = 0;
#       xend = image.width;
#       xinc = 1;
#     } else {
#       // odd numbered rows are right to left
#       xbegin = image.width - 1;
#       xend = -1;
#       xinc = -1;
#     }
#     for (x = xbegin; x != xend; x += xinc) {
#       for (int i=0; i < 8; i++) {
#         // fetch 8 pixels from the image, 1 for each pin
#         pixel[i] = image.pixels[x + (y + linesPerPin * i) * image.width];
#         pixel[i] = convert_RGB_2_GRB(pixel[i]);
#         // pixel[i] = pixel[i] % 20;
#         //  pixel[i] = pixel[i] & 0x1F1F1F;
#         pixel[i] = pixel[i] & 0xf0f0f0;
#         pixel[i] = pixel[i] >> 4;
#       }
#       // convert 8 pixels to 24 bytes
#       for (mask = 0x800000; mask != 0; mask >>= 1) {
#         byte b = 0;
#         for (int i=0; i < 8; i++) {
#           if ((pixel[i] & mask) != 0) b |= (1 << i);
#         }
#         data[offset++] = b;
#       }
#     }
#   }
# }
#
# int convert_RGB_2_GRB(int colour) {
#   int red = (colour & 0xFF0000) >> 16;
#   int green = (colour & 0x00FF00) >> 8;
#   int blue = (colour & 0x0000FF);
#
#   red = gammaTable[red];
#   green = gammaTable[green];
#   blue = gammaTable[blue];
#
#   return (green << 16) | (red << 8) | (blue);
# }
#
# // ask a Teensy board for its LED configuration, and set up the info for it.
# void serialConfigure(String portName) {
#   if (numberOfPortsInUse >= MaximumNumberOfPorts) {
#     println("too many serial ports, please increase maxPorts");
#     errorCount++;
#     return;
#   }
#   try {
#     ledSerial[numberOfPortsInUse] = new Serial(this, portName);
#     if (ledSerial[numberOfPortsInUse] == null) throw new NullPointerException();
#     ledSerial[numberOfPortsInUse].write('?');
#   }
#   catch (Throwable e) {
#     println("Serial port " + portName + " does not exist or is non-functional");
#     errorCount++;
#     return;
#   }
#   delay(50);
#   String line = ledSerial[numberOfPortsInUse].readStringUntil(10);
#   if (line == null) {
#     println("Serial port " + portName + " readStringUntilis not responding.");
#     println("Is it really a Teensy 3.0 running VideoDisplay?");
#     errorCount++;
#     return;
#   }
#   String param[] = line.split(",");
#   if (param.length != 12) {
#     println("Error: port " + portName + " did not respond to LED config query");
#     errorCount++;
#     return;
#   }
#   // only store the info and increase numPorts if Teensy responds properly
#   ledImage[numberOfPortsInUse] = new PImage(Integer.parseInt(param[0]), Integer.parseInt(param[1]), RGB);
#   // Note: rows and cols are according to the teensy, which is configured to be mounted rotated π/2
#   println("Panel", numberOfPortsInUse, "cols", param[0], "rows", param[1]);
#   ledArea[numberOfPortsInUse] = new Rectangle(Integer.parseInt(param[5]), Integer.parseInt(param[6]),
#     Integer.parseInt(param[7]), Integer.parseInt(param[8]));
#   println("xoff", param[5], "yoff", param[6], "width%", param[7], "height%", param[8]);
#   ledLayout[numberOfPortsInUse] = (Integer.parseInt(param[5]) == 0);
#   println("layout", param[5]);
#   numberOfPortsInUse++;
# }
#
# // scale a number by a percentage, from 0 to 100
# int percentage(int num, int percent) {
#   double mult = percentageFloat(percent);
#   double output = num * mult;
#   return (int)output;
# }
#
# // scale a number by the inverse of a percentage, from 0 to 100
# int percentageInverse(int num, int percent) {
#   double div = percentageFloat(percent);
#   double output = num / div;
#   return (int)output;
# }
#
# // convert an integer from 0 to 100 to a float percentage
# // from 0.0 to 1.0.  Special cases for 1/3, 1/6, 1/7, etc
# // are handled automatically to fix integer rounding.
# double percentageFloat(int percent) {
#   if (percent == 33) return 1.0 / 3.0;
#   if (percent == 17) return 1.0 / 6.0;
#   if (percent == 14) return 1.0 / 7.0;
#   if (percent == 13) return 1.0 / 8.0;
#   if (percent == 11) return 1.0 / 9.0;
#   if (percent ==  9) return 1.0 / 11.0;
#   if (percent ==  8) return 1.0 / 12.0;
#   return (double)percent / 100.0;
# }
