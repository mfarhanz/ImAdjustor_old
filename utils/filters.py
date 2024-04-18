from random import uniform

color_matrix = {
    'None': lambda _: (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0),
    'Custom': lambda val: (val[0], 0, 0, 0, 0, val[1], 0, 0, 0, 0, val[2], 0),
    'Factor': lambda val: (val/25+1, 0, 0, 0, 0, val/25+1, 0, 0, 0, 0, val/25+1, 0),
    'Intensity': lambda val: (1, 0, 0, val*1.2, 0, 1, 0, val*1.2, 0, 0, 1, val*1.2),
    'CIE_XYZ': lambda val: (0.412453, 0.357580, 0.180423, val, 0.212671, 0.715160,
                            0.072169, val, 0.019334, 0.119193, 0.950227, val),
    'CMYK': lambda val: (0.4124, 0.3576, 0.1805, val, 0.2126, 0.7152, 0.0722, val, 0.0193, 0.1192, 0.9505, val),
    'LAB': lambda val: (0.4124, 0.3576, 0.1805, val, 0.2126, 0.7152, 0.0722, val, 0.0193, 0.1192, 0.9505, val),
    'YUV': lambda val: (0.299, 0.587, 0.114, val, -0.14713, -0.28886, 0.436, val, 0.615, -0.51499, -0.10001, val),
    'Grayscale': lambda val: (0.299, 0.587, 0.114, val, 0.299, 0.587, 0.114, val, 0.299, 0.587, 0.114, val),
    'Sepia': lambda val: (0.393, 0.769, 0.189, val, 0.349, 0.686, 0.168, val, 0.272, 0.534, 0.131, val),
    'Tint(Cyan-Red)': lambda val: (1, 0, 0, val, 0, 1, 0, -val, 0, 0, 1, -val),
    'Tint(Magenta-Green)': lambda val: (1, 0, 0, -val, 0, 1, 0, val, 0, 0, 1, -val),
    'Tint(Yellow-Blue)': lambda val: (1, 0, 0, -val, 0, 1, 0, -val, 0, 0, 1, val),
    'Color Balance': lambda val: (1.5, 0, 0, val, 0, 1, 0, val, 0, 0, 0.8, val),
    'True Color': lambda val: (1.87, -0.79, -0.08, val, -0.20, 1.64, -0.44, val, 0.03, -0.55, 1.52, val),
    'Random': lambda val: (uniform(0.5, 0.8)+1/val, 0, 0, 0, 0, uniform(0.5, 0.6)+1/val, 0, 0,
                           0, 0, uniform(0.2, 0.6)+1/val, 0),
    'Bluish': lambda val: (-1, -2, -1, val, 1, 0, 0, val, 1, 0, 1, val),
    'Hellish': lambda val: (1, 0, 0, val, 0, 1, -1, val, 0, -1, 1, val),
    'Hellish 2': lambda val: (-1.8, 1, 0.8, val, -1, 0, 0, val, 0, -1, 1, val),
    'Hellish 3': lambda val: (0.3, -0.3, 0.9, val, 1.8, -1, 0, val, -1, 0, 0.4, val),
    'Ghostly': lambda val: (-1, 1, 0, val, -1, 0.5, 1, val, 0, 1, 1, val),
    'Evil': lambda val: (-1.8, 1, 0.8, val, -0.1, 0.3, 0, val, 0.5, -1, 1, val),
    'Evil 2': lambda val: (0, 3, -2, val, -1, 1, 0.2, val, -1, 1.4, -1, val),
    'Scary': lambda val: (0, -1, 0, val, 1, -0.45, 0, val, -1, 2, -1, val),
    'Scary 2': lambda val: (0, 0, 0, val, -2, 1, 0.6, val, -1, 1.4, -1, val),
    'Scary 2 (Hi-Contrast)': lambda val: (0, 0, 0, val, -1, -1, 2, val, -0.1, -0.9, 1.1, val),
    'Afterdark': lambda val: (-0.9, 0, 0, val, -0.5, -0.5, 0, val, 0.2, -0.9, 1.06, val),
}

filter_matrix = {
    'Blur': {
        'kernel': ((0.1111, 0.1111, 0.1111), (0.1111, 0.1111, 0.1111), (0.1111, 0.1111, 0.1111)),
        'type': 'convolution'
    },
    'Triangle Blur': {
        'kernel': ((0.0625, 0.125, 0.0625), (0.125, 0.25, 0.125), (0.0625, 0.125, 0.0625)),
        'type': 'convolution'
    },
    'Gaussian Blur': {
        'kernel': ((0.00390625, 0.015625, 0.0234375, 0.015625, 0.00390625),
                   (0.015625, 0.0625, 0.09375, 0.0625, 0.015625),
                   (0.0234375, 0.09375, 0.140625, 0.09375, 0.0234375),
                   (0.015625, 0.0625, 0.09375, 0.0625, 0.015625),
                   (0.00390625, 0.015625, 0.0234375, 0.015625, 0.00390625)),
        'type': 'convolution'
    },
    'Motion Blur': {
        'kernel': ((0, 0, 0.3333), (0, 0.3333, 0), (0.3333, 0, 0)),
        'type': 'convolution'
    },
    '1': '',
    'High Boost': {
        'kernel': ((-1, -1, -1), (-1, 9, -1), (-1, -1, -1)),
        'type': 'convolution'
    },
    'Emboss': {
        'kernel': ((-2, -1, 0), (-1,  1, 1), (0,  1, 2)),
        'type': 'convolution'
    },
    'Sharpen': {
        'kernel': ((0, -1,  0), (-1,  5, -1), (0, -1,  0)),
        'type': 'convolution'
    },
    '2': '',
    'Sobel Edge Detection (H)': {
        'kernel': ((-1, 0, 1), (-2, 0, 2), (-1, 0, 1)),
        'type': 'convolution'
    },
    'Sobel Edge Detection (V)': {
        'kernel': ((-1, -2, -1), (0, 0, 0), (1, 2, 1)),
        'type': 'convolution'
    },
    'Prewitt Edge Detection (H)': {
        'kernel': ((-1, -1, -1), (0, 0, 0), (1, 1, 1)),
        'type': 'convolution'
    },
    'Prewitt Edge Detection (V)': {
        'kernel': ((-1, 0, 1), (-1, 0, 1), (-1, 0, 1)),
        'type': 'convolution'
    },
    'Scharr Edge Detection (H)': {
        'kernel': ((-3, 0, 3), (-10, 0, 10), (-3, 0, 3)),
        'type': 'convolution'
    },
    'Scharr Edge Detection (V)': {
        'kernel': ((-3, -10, -3), (0, 0, 0), (3, 10, 3)),
        'type': 'convolution'
    },
    'Frei-Chen Edge Detection (H)': {
        'kernel': ((-1, -1.4142, -1), (0, 0, 0), (1, 1.4142, 1)),
        'type': 'convolution'
    },
    'Frei-Chen Edge Detection (V)': {
        'kernel': ((-1, 0, 1), (-1.4142, 0, 1.4142), (-1, 0, 1)),
        'type': 'convolution'
    },
    'Kirsch Compass Mask (N)': {
        'kernel': ((-3, -3, 5), (-3, 0, 5), (-3, -3, 5)),
        'type': 'convolution'
    },
    'Kirsch Compass Mask (NW)': {
        'kernel': ((-3, 5, 5), (-3, 0, 5), (-3, -3, -3)),
        'type': 'convolution'
    },
    'Kirsch Compass Mask (W)': {
        'kernel': ((5, 5, 5), (-3, 0, -3), (-3, -3, -3)),
        'type': 'convolution'
    },
    'Kirsch Compass Mask (SW)': {
        'kernel': ((5, 5, -3), (5, 0, -3), (-3, -3, -3)),
        'type': 'convolution'
    },
    'Kirsch Compass Mask (S)': {
        'kernel': ((5, -3, -3), (5, 0, -3), (5, -3, -3)),
        'type': 'convolution'
    },
    'Kirsch Compass Mask (SE)': {
        'kernel': ((-3, -3, -3), (5, 0, -3), (5, 5, -3)),
        'type': 'convolution'
    },
    'Kirsch Compass Mask (E)': {
        'kernel': ((-3, -3, -3), (-3, 0, -3), (5, 5, 5)),
        'type': 'convolution'
    },
    'Kirsch Compass Mask (NE)': {
        'kernel': ((-3, -3, -3), (-3, 0, 5), (-3, 5, 5)),
        'type': 'convolution'
    },
    'Laplacian': {
        'kernel': ((0, 1, 0), (1, -4, 1), (0, 1, 0)),
        'type': 'convolution'
    },
    'Inverse Laplacian': {
        'kernel': ((0, -1,  0), (-1,  4, -1), (0, -1,  0)),
        'type': 'convolution'
    },
    'High Pass': {
        'kernel': ((-1, -1, -1), (-1,  8, -1), (-1, -1, -1)),
        'type': 'convolution'
    },
    'Laplacian (5x5)': {
        'kernel': ((0, -2, -4, -2, 0), (-2, -4, 8, -4, -2), (-4, 8, 16, 8, -4), (-2, -4, 8, -4, -2),
                   (0, -2, -4, -2, 0)),
        'type': 'convolution'
    },
    'Farid Transform': {
        'kernel': ((-0.229879, 0.540242, 0.229879), (0.425827, 0, -0.425827), (0.229879, -0.540242, -0.229879)),
        'type': 'convolution'
    },
    'Derivative of Gaussian': {
        'kernel': ((-0.01724138, -0.03448276, 0, 0.03448276, 0.01724138),
                   (-0.06896552, -0.17241379, 0, 0.17241379, 0.06896552),
                   (-0.12068966, -0.29310345, 0, 0.29310345, 0.12068966),
                   (-0.06896552, -0.17241379, 0, 0.17241379, 0.06896552),
                   (-0.01724138, -0.03448276, 0, 0.03448276, 0.01724138)),
        'type': 'convolution'
    },
    'Laplacian of Gaussian': {
        'kernel': ((0, 0, 0.0125, 0.0125, 0.0125, 0, 0),
                   (0, 0.0125, 0.0625, 0.075, 0.0625, 0.0125, 0),
                   (0.0125, 0.0625, 0, -0.1375, 0, 0.0625, 0.0125),
                   (0.0125, 0.075, -0.1375, -0.45, -0.1375, 0.075, 0.0125),
                   (0.0125, 0.0625, 0, -0.1375,  0, 0.0625, 0.0125),
                   (0, 0.0125, 0.0625, 0.075, 0.0625, 0.0125, 0),
                   (0, 0, 0.0125, 0.0125, 0.0125, 0, 0)),
        'type': 'convolution'
    },
    '3': '',
    'Negative': {
        'kernel': ((0, 0, 0), (0, -1, 0), (0, 0, 0)),
        'type': 'convolution'
    },
    'HVS1': {
        'kernel': ((0.00085, 0.00166, 0.00294, 0.00458, 0.0061, 0.00674, 0.0061, 0.00458, 0.00294, 0.00166, 0.00085),
                   (0.00166, 0.00349, 0.00674, 0.01142, 0.01619, 0.01832, 0.01619, 0.01142, 0.00674, 0.00349, 0.00166),
                   (0.00294, 0.00674, 0.01437, 0.02717, 0.04233, 0.04979, 0.04233, 0.02717, 0.01437, 0.00674, 0.00294),
                   (0.00294, 0.00674, 0.01437, 0.02717, 0.04233, 0.04979, 0.04233, 0.02717, 0.01437, 0.00674, 0.00294),
                   (0.0061, 0.01619, 0.04233, 0.10688, 0.24312, 0.36788, 0.24312, 0.10688, 0.04233, 0.01619, 0.0061),
                   (0.00674, 0.01832, 0.04979, 0.13534, 0.36788, 1.0, 0.36788, 0.13534, 0.04979, 0.01832, 0.00674),
                   (0.0061, 0.01619, 0.04233, 0.10688, 0.24312, 0.36788, 0.24312, 0.10688, 0.04233, 0.01619, 0.0061),
                   (0.00458, 0.01142, 0.02717, 0.05911, 0.10688, 0.13534, 0.10688, 0.05911, 0.02717, 0.01142, 0.00458),
                   (0.00294, 0.00674, 0.01437, 0.02717, 0.04233, 0.04979, 0.04233, 0.02717, 0.01437, 0.00674, 0.00294),
                   (0.00166, 0.00349, 0.00674, 0.01142, 0.01619, 0.01832, 0.01619, 0.01142, 0.00674, 0.00349, 0.00166),
                   (0.00085, 0.00166, 0.00294, 0.00458, 0.0061, 0.00674, 0.0061, 0.00458, 0.00294, 0.00166, 0.00085)),
        'type': 'convolution'
    },
    'HVS2': {
        'kernel': ((0.00193, 0.00595, 0.01426, 0.02665, 0.03877, 0.04394, 0.03877, 0.02665, 0.01426, 0.00595, 0.00193),
                   (0.00595, 0.01832, 0.04394, 0.08208, 0.11943, 0.13534, 0.11943, 0.08208, 0.04394, 0.01832, 0.00595),
                   (0.01426, 0.04394, 0.1054, 0.19691, 0.2865, 0.32465, 0.2865, 0.19691, 0.1054, 0.04394, 0.01426),
                   (0.02665, 0.08208, 0.19691, 0.36788, 0.53526, 0.60653, 0.53526, 0.36788, 0.19691, 0.08208, 0.02665),
                   (0.03877, 0.11943, 0.2865, 0.53526, 0.7788, 0.8825, 0.7788, 0.53526, 0.2865, 0.11943, 0.03877),
                   (0.04394, 0.13534, 0.32465, 0.60653, 0.8825, 1.0, 0.8825, 0.60653, 0.32465, 0.13534, 0.04394),
                   (0.03877, 0.11943, 0.2865, 0.53526, 0.7788, 0.8825, 0.7788, 0.53526, 0.2865, 0.11943, 0.03877),
                   (0.02665, 0.08208, 0.19691, 0.36788, 0.53526, 0.60653, 0.53526, 0.36788, 0.19691, 0.08208, 0.02665),
                   (0.01426, 0.04394, 0.1054, 0.19691, 0.2865, 0.32465, 0.2865, 0.19691, 0.1054, 0.04394, 0.01426),
                   (0.00595, 0.01832, 0.04394, 0.08208, 0.11943, 0.13534, 0.11943, 0.08208, 0.04394, 0.01832, 0.00595),
                   (0.00193, 0.00595, 0.01426, 0.02665, 0.03877, 0.04394, 0.03877, 0.02665, 0.01426, 0.00595, 0.00193)),
        'type': 'convolution'
    },
    '4': '',
    'Row Dither': {
        'kernel': ((0, ), (1, )),
        'type': 'ordered dither'
    },
    'Bayer Dither (2x2)': {
        'kernel': ((0, 0.5), (0.75, 0.25)),
        'type': 'ordered dither'
    },
    'Bayer Dither (3x3)': {
        'kernel': ((0.1111, 0.4444, 0.7778), (0.6667, 0, 0.2222), (0.3333, 0.8889, 0.5556)),
        'type': 'ordered dither'
    },
    'Bayer Dither (4x4)': {
        'kernel': ((0, 0.5, 0.125, 0.625), (0.75, 0.25, 0.875, 0.375),
                   (0.1875, 0.6875, 0.0625, 0.5625), (0.9375, 0.4375, 0.8125, 0.3125)),
        'type': 'ordered dither'
    },
    'Bayer Dither (8x8)': {
        'kernel': ((0, 0.75, 0.1875, 0.9375, 0.046875, 0.796875, 0.234375, 0.984375),
                   (0.5, 0.25, 0.6875, 0.9375, 0.4375, 0.546875, 0.296875, 0.734375),
                   (0.125, 0.875, 0.0625, 0.8125, 0.171875, 0.921875, 0.109375, 0.859375),
                   (0.625, 0.375, 0.5625, 0.3125, 0.671875, 0.421875, 0.609375, 0.359375),
                   (0.03125, 0.78125, 0.21875, 0.96875, 0.015625, 0.765625, 0.203125, 0.953125),
                   (0.53125, 0.28125, 0.71875, 0.46875, 0.515625, 0.265625, 0.703125, 0.453125),
                   (0.15625, 0.90625, 0.09375, 0.84375, 0.140625, 0.890625, 0.078125, 0.828125),
                   (0.65625, 0.40625, 0.59375, 0.34375, 0.640625, 0.390625, 0.578125, 0.328125)),
        'type': 'ordered dither'
    },
    'Checkerboard Dither (2x2)': {
        'kernel': ((1, 0), (0, 1)),
        'type': 'ordered dither'
    },
    'Checkerboard Dither (3x3)': {
        'kernel': ((1, 0, 1), (0, 1, 0), (1, 0, 1)),
        'type': 'ordered dither'
    },
    'Checkerboard Dither (4x4)': {
        'kernel': ((1, 0, 1, 0), (0, 1, 0, 1), (1, 0, 1, 0), (0, 1, 0, 0)),
        'type': 'ordered dither'
    },
    'Comb Dither (H)': {
        'kernel': ((0.6, 0.2, 0, 0.4, 0.8), (0.66667, 0.26667, 0.066667, 0.46667, 0.86667),
                   (0.73333, 0.33333, 0.13333, 0.53333, 0.93333)),
        'type': 'ordered dither'
    },
    'Comb Dither (V)': {
        'kernel': ((0.6, 0.6667, 0.7333), (0.2, 0.2667, 0.3333), (0, 0.0667, 0.1333),
                   (0.4, 0.4667, 0.5333), (0.8, 0.8667, 0.9333)),
        'type': 'ordered dither'
    },
    'Binary Thresh': {
        'kernel': (1,),
        'type': 'ordered dither'
    },
    'Non-Rectangular1 Dither': {
        'kernel': ((0.8333, 0.625, 0, 0.2083, 0.4167), (0, 0.2083, 0.4167, 0.8333, 0.625),
                   (0, 0.2083, 0.4167, 0.8333, 0.625), (0.625, 0, 0.2083, 0.4167, 0.8333),
                   (0.2083, 0.4167, 0.8333, 0.625, 0)),
        'type': 'ordered dither'
    },
    'Non-Rectangular2 Dither': {
        'kernel': ((0, 0.5, 0.25, 0), (0.75, 0, 0.625, 0.375), (0, 0.875, 0.125, 0)),
        'type': 'ordered dither'
    },
    'Non-Rectangular (8x8)': {
        'kernel': ((0.375, 0.5, 0.25, 0.875, 0.125, 0.75, 0, 0.625), (0.75, 0, 0.625, 0.375, 0.5, 0.25, 0.875, 0.125),
                   (0.25, 0.875, 0.125, 0.75, 0, 0.625, 0.375, 0.5), (0.625, 0.375, 0.5, 0.25, 0.875, 0.125, 0.75, 0),
                   (0.125, 0.75, 0, 0.625, 0.375, 0.5, 0.25, 0.875), (0.5, 0.25, 0.875, 0.125, 0.75, 0, 0.625, 0.375),
                   (0, 0.625, 0.375, 0.5, 0.25, 0.875, 0.125, 0.75), (0.875, 0.125, 0.75, 0, 0.625, 0.375, 0.5, 0.25)),
        'type': 'ordered dither'
    },
    'Ulichney Dither': {
        'kernel': ((0.75, 0.3125, 0.375, 0.8125), (0.25, 0, 0.0625, 0.4375),
                   (0.6875, 0.1875, 0.125, 0.5), (0.9375, 0.625, 0.5625, 0.875)),
        'type': 'ordered dither'
    },
    '45-Degree Dither (4x4)': {
        'kernel': ((0.4444, 0.2222, 0.7778, 0.5556), (0.3333, 0.1111, 0.8889, 0.6667),
                   (0.7778, 0.5556, 0.4444, 0.2222), (0.8889, 0.6667, 0.3333, 0.1111)),
        'type': 'ordered dither'
    },
    'Variable Dither (2x2)': {
        'kernel': ((-1.5, 1.5), (0.5, -0.5)),
        'type': 'ordered dither'
    },
    'Variable Dither (4x4)': {
        'kernel': ((-7.5,  0.5, -5.5,  2.5), (4.5, -3.5,  6.5, -1.5),
                   (-4.5,  3.5, -6.5,  1.5), (7.5, -0.5,  5.5, -2.5)),
        'type': 'ordered dither'
    },
    'TPDF Dither': {
        'kernel': ((0.25, 0.5, 0.75, 1), (0.5, 0.75, 1, 0.75), (0.75, 1, 0.75, 0.5),
                   (1, 0.75, 0.5, 0.25)),
        'type': 'ordered dither'
    },
    'Dispersed Dot (4x4)': {
        'kernel': ((0.375, 0.4375, 0.5, 0.5625), (0.3125, 0, 0.0625, 0.625),
                   (0.25, 0.1875, 0.125, 0.6875), (0.9375, 0.875, 0.8125, 0.75)),
        'type': 'ordered dither'
    },
    'Dispersed Dot (6x6)': {
        'kernel': ((0.8889, 0.4444, 0.5556, 0.9444, 0.5, 0.6111), (0.3333, 0, 0.1111, 0.3889, 0.0556, 0.1667),
                   (0.7778, 0.2222, 0.6667, 0.8333, 0.2778, 0.7222), (0.9722, 0.5278, 0.6389, 0.9167, 0.4722, 0.5833),
                   (0.4167, 0.0833, 0.1944, 0.3611, 0.02778, 0.1389), (0.8611, 0.3056, 0.75, 0.8056, 0.25, 0.6944)),
        'type': 'ordered dither'
    },
    'Clustered Dot (4x4)': {
        'kernel': ((0.75, 0.3125, 0.375, 0.8125), (0.25, 0, 0.0625, 0.4375),
                   (0.6875, 0.1875, 0.125, 0.5), (0.9375, 0.625, 0.5625, 0.875)),
        'type': 'ordered dither'
    },
    'Clustered Dot (5x5)': {
        'kernel': ((0.88, 0.56, 0.4, 0.68, 0.84), (0.72, 0.24, 0.08, 0.2, 0.52),
                   (0.44, 0.12, 0, 0.04, 0.36), (0.6, 0.28, 0.16, 0.32, 0.8), (0.92, 0.76, 0.48, 0.64, 0.96)),
        'type': 'ordered dither'
    },
    'Clustered Dot (6x6)': {
        'kernel': ((0.4444, 0.3333, 0.3889, 0.5, 0.6111, 0.5556),
                   (0.2778, 0, 0.05556, 0.6667, 0.9444, 0.8889),
                   (0.2222, 0.1667, 0.1111, 0.7222, 0.7778, 0.8333),
                   (0.5, 0.6111, 0.5556, 0.4444, 0.3333, 0.4444),
                   (0.6667, 0.9444, 0.8889, 0.2778, 0, 0.0556),
                   (0.7222, 0.7778, 0.8333, 0.2222, 0.1667, 0.1111)),
        'type': 'ordered dither'
    },
    'Clustered Dot (8x8)': {
        'kernel': ((0.375, 0.15625, 0.1875, 0.40625, 0.546875, 0.734375, 0.765625, 0.578125),
                   (0.125, 0, 0.03125, 0.21875, 0.703125, 0.921875, 0.953125, 0.796875),
                   (0.34375, 0.09375, 0.0625, 0.25, 0.671875, 0.890625, 0.984375, 0.828125),
                   (0.46875, 0.3125, 0.28125, 0.4375, 0.515625, 0.640625, 0.859375, 0.609375),
                   (0.53125, 0.71875, 0.75, 0.5625, 0.390625, 0.171875, 0.203125, 0.421875),
                   (0.6875, 0.90625, 0.9375, 0.78125, 0.140625, 0.015625, 0.046875, 0.234375),
                   (0.65625, 0.875, 0.96875, 0.8125, 0.359375, 0.109375, 0.078125, 0.265625),
                   (0.5, 0.625, 0.84375, 0.59375, 0.484375, 0.328125, 0.296875, 0.453125)),
        'type': 'ordered dither'
    },
    'Floyd-Steinberg Dither': {
        'kernel': ((0, 0, 0), (0, 1, 0.4375), (0.1875, 0.3125, 0.0625)),
        'type': 'error diffusion'
    },
    'Jarvis-Judice-Ninke Dither': {
        'kernel': ((0, 0, 0, 0, 0), (0, 0, 0, 0, 0,), (0, 0, 1, 0.145833, 0.104167),
                   (0.0625, 0.104167, 0.145833, 0.104167, 0.0625),
                   (0.02083333, 0.0625, 0.10416667, 0.0625, 0.02083333)),
        'type': 'error diffusion'
    },
    'Stucki Dither': {
        'kernel': ((0, 0, 0, 0, 0), (0, 0, 0, 0, 0), (0, 0, 1, 0.190476, 0.095238),
                   (0.047619, 0.095238, 0.190476, 0.095238, 0.047619),
                   (0.023809, 0.047619, 0.095238, 0.047619, 0.023809)),
        'type': 'error diffusion'
    },
    'Atkinson Dither': {
        'kernel': ((0, 0, 0, 0, 0), (0, 0, 0, 0, 0), (0, 0, 1, 0.125, 0.125),
                   (0, 0.125, 0.125, 0.125, 0), (0, 0, 0.125, 0, 0)),
        'type': 'error diffusion'
    },
    'Burkes Dither': {
        'kernel': ((0, 0, 0, 0, 0), (0, 0, 0, 0, 0), (0, 0, 1, 0.25, 0.125),
                   (0.0625, 0.125, 0.25, 0.125, 0.0625), (0, 0, 0, 0, 0)),
        'type': 'error diffusion'
    },
    'Sierra Dither': {
        'kernel': ((0, 0, 0, 0, 0), (0, 0, 0, 0, 0), (0, 0, 1, 0.15625, 0.09375),
                   (0.0625, 0.125, 0.15625, 0.125, 0.0625), (0, 0.0625, 0.09375, 0.0625, 0)),
        'type': 'error diffusion'
    },
    'Sierra 2-Row Dither': {
        'kernel': ((0, 0, 1, 0.25, 0.1875), (0.0625, 0.125, 0.1875, 0.125, 0.0625)),
        'type': 'error diffusion'
    },
    'Sierra Lite Dither': {
        'kernel': ((0, 1, 0.5), (0.25, 0.25, 0)),
        'type': 'error diffusion'
    },
    'Fan Dither': {
        'kernel': ((0, 0, 1, 0.4375), (0.0625, 0.1875, 0.3125, 0)),
        'type': 'error diffusion'
    },
    'Shiau-Fan Dither': {
        'kernel': ((0, 0, 1, 0.5), (0.125, 0.125, 0.25, 0)),
        'type': 'error diffusion'
    },
    'Shiau-Fan2 Dither': {
        'kernel': ((0, 0, 0, 1, 0.5), (0.0625, 0.0625, 0.125, 0.25, 0)),
        'type': 'error diffusion'
    },
    'Stevenson-Arce Dither': {
        'kernel': ((0, 0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0, 0),
                   (0, 0, 0, 1, 0, 0.16, 0), (0.06, 0, 0.13, 0, 0.15, 0, 0.08),
                   (0, 0.06, 0, 0.13, 0, 0.06, 0), (0.025, 0, 0.06, 0, 0.06, 0, 0.025)),
        'type': 'error diffusion'
    },
    'Steve-Pigeon Dither': {
        'kernel': ((0, 0, 1, 0.14285714, 0.07142857),
                   (0, 0.14285714, 0.14285714, 0.14285714, 0),
                   (0.07142857, 0, 0.07142857, 0, 0.07142857)),
        'type': 'error diffusion'
    },

}
