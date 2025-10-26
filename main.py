from step_viewer import StepViewer


# -------------------------
# Punkt wejścia
# -------------------------
if __name__ == "__main__":
    # Przykładowa lista plików (podstawić rzeczywiste ścieżki)
    filenames = [
        "ramie0.step", "ramie1.step", "ramie2.step",
        "ramie3.step", "ramie4.step", "ramie5.step", "ramie6.step",
    ]

    viewer = StepViewer(filenames=filenames, cache_dir=".cache", marker_radius=10.0)
    viewer.run()
