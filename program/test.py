message = 'Hello world testing message'
sending_message = ''
for i in range(0, len(message), 2):
    fliped_pair = message[i:i+2][::-1] + ' '
    if len(fliped_pair) > 2:
        sending_message = ''.join([sending_message, fliped_pair])

print(sending_message)

counter = 0
for i in range(0, len(sending_message), 3):
    counter += 1

print(counter)
