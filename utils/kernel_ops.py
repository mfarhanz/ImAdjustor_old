from multiprocessing import Process, Array
from numpy import pad, einsum, frombuffer, stack, float64

def convolve(arr, fltr, output_arr, pad_len):
    padded_arr = pad(arr, pad_len, mode='edge')
    for x1 in range(pad_len, padded_arr.shape[0] - pad_len):
        for y1 in range(pad_len, padded_arr.shape[1] - pad_len):
            output_arr[x1*padded_arr.shape[1]+y1] = einsum('ij,ij',
                                                           padded_arr[x1 - pad_len: x1 + pad_len+1,
                                                           y1 - pad_len: y1 + pad_len+1], fltr)
    return output_arr

def error_diffuse(arr, filtr, output_arr, pad_len):
    pass

def ordered_dither(arr, filtr, output_arr, _):
    for x1 in range(0, arr.shape[0]):
        for y1 in range(0, arr.shape[1]):
            check = filtr[x1 % len(filtr)][y1 % len(filtr[0])] * 255
            output_arr[x1 * arr.shape[1] + y1] = 0 if arr[x1][y1] < check else 255
    return output_arr


def channel_op(size, channels, kernel, op_type):
    process_channels = [Array('d', size) for _ in range(3)]
    pad_len = len(kernel) // 2
    processes = []
    for i in range(3):
        p = Process(target=convolve if op_type == 'convolution' else error_diffuse if op_type == 'error diffusion'
                    else ordered_dither, args=(channels[i], kernel, process_channels[i], pad_len))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()
    match op_type:
        case 'convolution':
            process_channels[:] = [frombuffer(arr.get_obj(), dtype=float64)
                                 .reshape((channels[0].shape[0]+2*pad_len, channels[0].shape[1]+2*pad_len))
                                 [pad_len:-pad_len, pad_len:-pad_len] for arr in process_channels]
        case 'ordered dither':
            process_channels[:] = [frombuffer(arr.get_obj(), dtype=float64).reshape(channels[0].shape)
                                   for arr in process_channels]
    return stack(process_channels, axis=2)
