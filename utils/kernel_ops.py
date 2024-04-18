from numpy import pad, einsum, arange, where, round as npround, \
    mod, abs as npabs, round as npround, frombuffer, newaxis,\
    reshape, zeros_like, vstack, sum as npsum, transpose, array, argmin, copy, clip, uint8
from numpy.lib.stride_tricks import as_strided
from numpy.random import uniform, randint

def convolve(arr, fltr, output_arr, pad_len):
    padded_arr = pad(arr, pad_len, mode='edge')
    window_size = fltr.shape
    window_shape = (padded_arr.shape[0] - window_size[0] + 1,
             padded_arr.shape[1] - window_size[1] + 1) + window_size
    strides = padded_arr.strides * 2
    windows_view = as_strided(padded_arr, shape=window_shape, strides=strides)
    res = einsum('ijkl,kl', windows_view, fltr)
    ret = frombuffer(output_arr.get_obj(), dtype='i').reshape(res.shape)
    ret[:, :] = res[:]
    del windows_view, padded_arr, res
    return output_arr

def ordered_dither(arr, fltr, output_arr, theta, dither_method):
    if len(fltr.shape) > 1:
        fltr = fltr * 255
        x_indices = arange(arr.shape[0])[:, newaxis] % fltr.shape[0]
        y_indices = arange(arr.shape[1]) % fltr.shape[1]
        check_values = fltr[x_indices, y_indices]
    if len(fltr.shape) == 1:
        res = where(arr < theta, 0, 255)
    elif dither_method == 'Min-Max (Inverted)':
        res = where(arr < check_values, 255, 0)
    elif dither_method == 'Set to Matrix':
        res = where(arr < check_values, arr, check_values*2)
    elif dither_method == 'Set to Matrix (Inverted)':
        res = where(arr < check_values, arr*2, check_values)
    elif dither_method == 'Round':
        res = where(arr < check_values, npround(arr / theta) * 5, arr)
    elif dither_method == 'Rounded Modulo':
        res = where(arr < check_values, mod((arr + check_values), 255), mod((arr - check_values), 255)*2)
    elif dither_method == 'Gamma Correct':
        gamma = 0.7+((theta-5)/245)*1.5
        res = where(arr ** (1/gamma) < check_values, arr ** (1/gamma), arr ** (1/(gamma-0.05)))
    elif dither_method == 'Perturb':
        res = where(arr < check_values + uniform(-theta//8, theta//8, size=check_values.shape), 0, 255)
    else:
        res = where(arr < check_values, 0, 255)
    ret = frombuffer(output_arr.get_obj(), dtype='i').reshape(res.shape)
    ret[:, :] = res[:]
    return output_arr

def error_diffuse(arr, filtr, output_arr, theta, dither_method):
    # diff = npabs((arr - npround(arr / theta) * theta))
    # windows = einsum('ij,kl->ijkl', diff, filtr)
    # res_first_half = [windows[:, :, i].reshape(arr.shape[0], -1) for i in range(filtr.shape[0])]
    # first_half_main = res_first_half.pop(filtr.shape[0] // 2)
    # del res_first_half[:filtr.shape[0] // 2]
    # res_first_half[:] = [vstack((zeros_like(arr[-i - 1:]), arr[:-i - 1])) for i, arr in enumerate(res_first_half)]
    # first_half_main = npsum([first_half_main, *res_first_half], axis=0)
    # second_half = transpose(first_half_main).reshape((arr.shape[1], filtr.shape[0], arr.shape[0]))
    # res_second_half = [second_half[:, i, :] for i in range(filtr.shape[0])]
    # second_half_main = res_second_half.pop(filtr.shape[0] // 2)
    # res_second_half[:len(res_second_half) // 2] = [vstack((zeros_like(arr[:i + 1]), arr[i + 1:]))
    #                                                for i, arr in enumerate(res_second_half[:len(res_second_half) // 2])]
    # res_second_half[len(res_second_half) // 2:] = [vstack((arr[:-i - 1], zeros_like(arr[-i - 1:])))
    #                                                for i, arr in enumerate(res_second_half[len(res_second_half) // 2:])]
    # second_half_main = npsum([second_half_main, *res_second_half], axis=0)
    # res = transpose(second_half_main)

    # newpix = npround(arr / 255) * 255
    # error = arr - newpix
    # sliced_error = error[1:-1, 1:-1]
    # sliced_newpix = newpix[1:-1, 1:-1]
    # arr[1:-1, 1:-1] = sliced_newpix
    # arr[1:-1, 2:] += (sliced_error * 7 / 16).astype(arr.dtype)
    # arr[2:, :-2] += (sliced_error * 3 / 16).astype(arr.dtype)
    # arr[2:, 2:] += (sliced_error * 5 / 16).astype(arr.dtype)
    # arr[2:, 2:] += (sliced_error * 1 / 16).astype(arr.dtype)
    # res = arr.astype(uint8)


    # for y in range(1, arr.shape[0] - 1):
    #     for x in range(1, arr.shape[1] - 1):
    #         pix = arr[y][x]
    #         newpix = round(pix / 255) * 255
    #         error = pix - newpix
    #         arr[y][x] = newpix
    #         arr[y][x + 1] += error * 7 / 16
    #         arr[y + 1][x - 1] += error * 3 / 16
    #         arr[y + 1][x] += error * 5 / 16
    #         arr[y + 1][x + 1] += error * 1 / 16
    # arr = clip(arr, 0, 250)
    # res = copy(arr.astype(uint8))


    ret = frombuffer(output_arr.get_obj(), dtype='i').reshape(res.shape)
    ret[:, :] = res[:]
    return output_arr
