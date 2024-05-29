
img * scale = screen 

img1 = (4096, 4096)
canvas = (4096, 4096)
factor = 1.1
scale = min(canvas [0] / img1[0], canvas [1] / img1[1])
print(scale)
for i in range (0,10):
    print (i)
    size = int(img1[0] * (factor ** i) * scale) , int(img1[0] * (factor ** i) * scale)
    print (size)
