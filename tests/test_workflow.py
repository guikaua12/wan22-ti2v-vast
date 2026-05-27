from executor.workflow import build_workflow


def test_build_workflow_injects_scene_fields():
    workflow = build_workflow({
        "pipelineSceneId": "scene-1",
        "inputImageUrl": "https://cdn.example/frame.jpg",
        "prompt": "show product",
        "negativePrompt": "blur",
        "width": 704,
        "height": 1280,
        "frameCount": 121,
        "fps": 24,
        "workflow": {"steps": 30, "cfg": 5.0, "sampler": "uni_pc", "scheduler": "simple"},
    })
    assert workflow["6"]["inputs"]["text"] == "show product"
    assert workflow["7"]["inputs"]["text"] == "blur"
    assert workflow["57"]["inputs"]["image"] == "https://cdn.example/frame.jpg"
    assert workflow["55"]["inputs"]["width"] == 704
    assert workflow["55"]["inputs"]["height"] == 1280
