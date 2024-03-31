from numpy import pad, einsum, arange, where, round, mod, frombuffer, copyto, newaxis, float64
from numpy.lib.stride_tricks import as_strided

def convolve(arr, fltr, output_arr, pad_len):
    padded_arr = pad(arr, pad_len, mode='edge')
    window_size = fltr.shape
    window_shape = (padded_arr.shape[0] - window_size[0] + 1,
             padded_arr.shape[1] - window_size[1] + 1) + window_size
    strides = padded_arr.strides * 2
    windows_view = as_strided(padded_arr, shape=window_shape, strides=strides)
    res = einsum('ijkl,kl', windows_view, fltr)
    ret = frombuffer(output_arr.get_obj(), dtype='d').reshape(res.shape)
    ret[:, :] = res[:]
    del windows_view, padded_arr, res
    return output_arr


def ordered_dither(arr, fltr, output_arr, dither_method):
    fltr = fltr * 255
    x_indices = arange(arr.shape[0])[:, newaxis] % fltr.shape[0]
    y_indices = arange(arr.shape[1]) % fltr.shape[1]
    check_values = fltr[x_indices, y_indices]
    if dither_method == 'inv_min_max':
        res = where(arr < check_values, 255, 0)
    elif dither_method == 'set_to_matrix':
        res = where(arr < check_values, arr, check_values)
    elif dither_method == 'round':
        res = where(arr < check_values, round(arr / 20) * 10, arr)
    elif dither_method == 'mod_round':
        res = where(arr < check_values, mod((arr + check_values), 255), mod((arr - check_values), 255))
    elif dither_method == 'gamma_correct':
        res = where(arr ** 0.9 < check_values, arr ** 0.9, arr ** 0.98)
    else:
        res = where(arr < check_values, 0, 255)
    ret = frombuffer(output_arr.get_obj(), dtype='d').reshape(res.shape)
    ret[:, :] = res[:]
    return output_arr


def error_diffuse(arr, filtr, output_arr, pad_len, dither_method):
    padded_arr = pad(arr, pad_len, mode='edge')
    print(len(output_arr), padded_arr.shape)
    init_out = frombuffer(output_arr.get_obj(), dtype=float64).reshape(padded_arr.shape)
    copyto(init_out, padded_arr)
    print(padded_arr.shape, init_out.shape)
    print(padded_arr[20, 20], init_out[20, 20])
    # for x1 in range(pad_len, padded_arr.shape[0] - pad_len):
    #     for y1 in range(pad_len, padded_arr.shape[0] - pad_len):

# def channel_op(size, channels, kernel, op_type, dither_opt):
#     process_channels = [Array('d', channels[0].shape[0]*channels[0].shape[1]) for _ in range(3)]
#     pad_len = len(kernel) // 2
#     processes = []
#     for i in range(3):
#         p = Process(target=convolve if op_type == 'convolution' else error_diffuse if op_type == 'error diffusion'
#                     else ordered_dither, args=
#                     (channels[i], kernel, process_channels[i], pad_len) if op_type == 'convolution' else
#                     (channels[i], kernel, process_channels[i], pad_len, dither_opt) if op_type == 'error diffusion' else
#                     (channels[i], kernel, process_channels[i], dither_opt))
#         processes.append(p)
#         p.start()
#     for p in processes:
#         p.join()
#     match op_type:
#         case 'convolution' | 'error diffusion':
#             process_channels[:] = [frombuffer(arr.get_obj(), dtype=float64).reshape(channels[0].shape) for arr in process_channels]
#             # process_channels[:] = [frombuffer(arr.get_obj(), dtype=float64)
#             #                      .reshape((channels[0].shape[0]+2*pad_len, channels[0].shape[1]+2*pad_len))
#             #                      [pad_len:-pad_len, pad_len:-pad_len] for arr in process_channels]
#         case 'ordered dither':
#             process_channels[:] = [frombuffer(arr.get_obj(), dtype=float64).reshape(channels[0].shape)
#                                    for arr in process_channels]
#     return stack(process_channels, axis=2)
