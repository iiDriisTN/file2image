from PIL import Image
import imageio
import os
from shutil import rmtree
import codecs
import binascii


# encoding...
# 0 is black pixel, white is 1

# writes a gif in parent_folder made up of all its sorted .png files
def make_gif(parent_folder, fname):
    items = os.listdir(parent_folder)
    png_filenames = []
    for elem in items:
        if elem.find(".png") != -1:
            png_filenames.append(elem)

    sorted_png = []
    while True:
        lowest = 10000000
        lowest_idx = -1
        for p in png_filenames:
            val = int(p.split("-")[1].split(".")[0])
            if lowest_idx == -1 or val < lowest:
                lowest = val
                lowest_idx = png_filenames.index(p)
        sorted_png.append(png_filenames[lowest_idx])
        del png_filenames[lowest_idx]
        if len(png_filenames) == 0:
            break
    png_filenames = sorted_png

    with imageio.get_writer(fname + ".gif", mode='I', duration=0.1) as writer:
        for filename in png_filenames:
            image = imageio.imread(parent_folder + "/" + filename)
            writer.append_data(image)
    return fname + ".gif"

# provided a list of pixels, writes it out as an image
# with the specified resolution
def pixels_2_png(pixels, fname):
    img = Image.new('RGB', (3840, 2160), color=(255, 255, 255))  # White background for PNG
    img.putdata(pixels)
    img.save(fname, format="PNG")
    print("pixels_2_png: Saved %d pixels to %s" % (len(pixels), fname))

# provided a filename, reads the png and returns a list of pixels
def png_2_pixels(fname):
    im = Image.open(fname)
    pixel_list = list(im.getdata())
    print("png_2_pixels: Read %d pixels from %s" % (len(pixel_list), fname))
    return pixel_list

# writes out the bits as binary to a file
def bits_2_file(bits, fname):
    with open(fname, 'wb') as f:
        idx = 0
        inc = 8
        while True:
            char = ''.join(bits[idx:idx + inc])
            f.write(bytes([int(char, 2)]))  # Convert to bytes and write to file
            idx += inc
            if idx >= len(bits):
                break
    print("bits_2_file: Wrote %d bits to %s" % (len(bits), fname))

# returns a list of bits in the file
def file_2_bits(fname):
    bits = []
    f = open(fname, "rb")
    try:
        byte = f.read(1)
        while byte != "":
            cur_bits = bin(ord(byte))[2:]
            while len(cur_bits) < 8:
                cur_bits = "0" + cur_bits
            for b in cur_bits:
                bits.append(b)
            byte = f.read(1)
    except Exception as e:
        print("Error while reading file:", e)
    finally:
        f.close()

    # Print some debugging information
    print("Number of bytes read:", len(bits) // 8)
    print("First few bits:", bits[:32])
    print("Last few bits:", bits[-32:])

    return bits

# converts a list of 0/1 bits to pixels
def bits_2_pixels(bits):
    pixels = []
    for b in bits:
        pixels.append((0, 0, 0) if b == '0' else (255, 255, 255))
    print("bits_2_pixels: Converted %d bits to %d pixels" % (len(bits), len(pixels)))
    return pixels

# converts opposite of bits_2_pixels
def pixels_2_bits(pixels):
    bits = []
    for p in pixels:
        bits.append('0' if p == (0, 0, 0) else '1')
    print("pixels_2_bits: Converted %d pixels to %d bits" % (len(pixels), len(bits)))
    return bits

def add_header(bits, fname):
    # filename encoded as ascii --> binary
    fname_bitstr = bin(int(binascii.hexlify(fname.encode('utf-8')), 16))
    
    print("add_header: fname_bitstr length %d" % len(fname_bitstr))

    # extra 2 bytes (16 bits) before header tells how long header is (in bits)
    fname_bitstr_length_bitstr = "{0:b}".format(len(fname_bitstr) - 2)

    while len(fname_bitstr_length_bitstr) < 16:
        fname_bitstr_length_bitstr = "0" + fname_bitstr_length_bitstr

    # length header to tell how long the rest of the header is, as well as the header itself
    fname_headers = fname_bitstr_length_bitstr + fname_bitstr[2:]

    # converting the string header to a list
    header_list = []
    for char in fname_headers:
        header_list.append(char)

    # secondary header after filename to tell how many bits the payload is
    # length of secondary header is 64 bits to allow for massive payload sizes
    payload_length_header = "{0:b}".format(len(bits))

    print("bits in payload: %d" % len(bits))

    while len(payload_length_header) < 64:
        payload_length_header = "0" + payload_length_header

    # append the secondary header to the main header
    for char in payload_length_header:
        header_list.append(char)

    total_header_length = len(header_list)

    # append the original bits onto the header and return
    header_list.extend(bits)
    #print "add_header: Added %d length header, total bits: %d" % (len(total_header), len(header_list))

    #print "add_header: total_header: %s" % ''.join(header_list[:total_header_length])
    return header_list

# takes in the bits, decodes the header into a filename.
# returns the filename, as well as the rest of the bits 
# after the header section
def decode_header(bits):
    # Helper function, converts a binary string (eg. '10101') to ASCII characters
    def decode_binary_string(s):
        return ''.join(chr(int(s[i*8:i*8+8], 2)) for i in range(len(s) // 8))

    # First 16 bits store the length of the filename (in bits)
    fname_length_binstr = ''.join(bits[:16])

    # Converting filename length to integer
    fname_length = int(fname_length_binstr, 2)
    print("decode_header: fname_length: %d" % fname_length)

    # Next fname_length bits are the ASCII filename
    fname_binstr = ''.join(bits[16:16 + fname_length])
    fname_binstr = "0" + fname_binstr

    # Convert the fname bitstring to ASCII using codecs with UTF-8 encoding
    fname_bytes = int(fname_binstr, 2).to_bytes((len(fname_binstr) + 7) // 8, 'big')
    fname = codecs.decode(fname_bytes, 'utf-8')
    print("decode_header: fname: %s" % fname)

    # Now need to decode the size of the payload
    payload_length_binstr = ''.join(bits[16 + fname_length:16 + fname_length + 64])

    # Convert the payload length to integer
    payload_length = int(payload_length_binstr, 2)
    print("decode_header: payload_length: %d" % payload_length)


    return fname, bits[16 + fname_length + 64:16 + fname_length + 64 + payload_length]

# provided two lists of bits, ensures both are identical,
# if not, reports the difference
def test_bit_similarity(bits1, bits2):
    f = open("bits.txt", "w")
    for b1 in bits1:
        f.write(b1)
    f.write("\n")
    for b2 in bits2:
        f.write(b2)
    f.write("\n")
    f.close()

    if len(bits1) != len(bits2):
        print("Bit lengths are not the same!")
        return
    for b1, b2 in zip(bits1, bits2):
        if b1 != b2:
            print("Bits are not the same!")
            return
    print("Bits are identical")

# provided a relative path, deletes the folder then creates a new version
# under the same name
def clear_folder(relative_path):
    try:
        rmtree(relative_path)
    except:
        print("WARNING: Could not locate /temp directory.")

    for i in range(10):
        try:
            os.mkdir(relative_path)
            break
        except:
            continue

def encode(src):
    bits = file_2_bits(src)
    bits = add_header(bits, src.split("/")[-1])
    pixels = bits_2_pixels(bits)

    # get the total number of pixels in a single image
    pixels_per_image = 3840 * 2160

    # get the number of images required to hold the entire file
    num_imgs = int(len(pixels) / pixels_per_image) + 1

    print("encode: Encoding will require %d .png frames" % num_imgs)

    # filename without any path specifiers
    name_clean = src.split("/")[-1]

    # clear the /temp folder
    try:
        rmtree("temp")
    except:
        print("WARNING: Could not locate /temp directory.")

    for i in range(10):
        try:
            os.mkdir("temp")
            break
        except:
            continue

    # create each of the png's
    for i in range(num_imgs):
        cur_temp_name = "temp/" + name_clean + "-" + str(i) + ".png"
        cur_start_idx = i * pixels_per_image
        cur_span = min(pixels_per_image, len(pixels) - cur_start_idx)
        cur_pixels = pixels[cur_start_idx:cur_start_idx + cur_span]
        pixels_2_png(cur_pixels, cur_temp_name)
        if cur_span < pixels_per_image:
            break

    # create gif from png sequence
    gif_name = make_gif("temp", name_clean)
    return gif_name

# provided a source .gif, decodes it back into the original file
def decode(src):
    # helper function to allow for iteration over .png's inside .gif
    def iter_frames(im):
        try:
            i = 0
            while 1:
                im.seek(i)
                imframe = im.copy()
                imframe = imframe.convert('RGB')
                yield imframe
                i += 1
        except EOFError:
            pass

    # load .gif
    im = Image.open(src)

    # save each frame individually
    saved_frames = []
    for i, frame in enumerate(iter_frames(im)):
        cur_frame = "temp/frame-%d.png" % i
        saved_frames.append(cur_frame)
        frame.save(cur_frame, **frame.info)

    print("decode: Identified %d .png frames" % len(saved_frames))

    # convert each png to pixels
    pixels = []
    for s in saved_frames:
        cur_pixels = png_2_pixels(s)
        pixels.extend(cur_pixels)

    # convert all pixels to bits
    bits = pixels_2_bits(pixels)

    # decode the filename
    fname, bits = decode_header(bits)

    # write out the file
    bits_2_file(bits, fname.split(".")[0] + "-recovered." + fname.split(".")[1])


def main():
    encode("359027545_6337496933000264_6892620266026037404_n.mp4")
    #decode("359027545_6337496933000264_6892620266026037404_n.mp4.gif")


if __name__ == '__main__':
    main()
