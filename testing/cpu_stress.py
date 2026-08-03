import multiprocessing

def cpu_load():
    while True:
        x = 0
        for i in range(10000000):
            x += i * i

if __name__ == "__main__":
    processes = []

    for _ in range(multiprocessing.cpu_count()):
        p = multiprocessing.Process(target=cpu_load)
        p.start()
        processes.append(p)

    for p in processes:
        p.join()