"""Shared model inference helpers for the API and Streamlit interfaces."""

import torch
import torch.nn.functional as F


def predict_with_cam(model, x, allowed_classes=None):
    """Average original/horizontal-flip predictions and explain the original view."""
    activations, gradients = [], []

    def capture_activation(module, inputs, output):
        _ = module, inputs
        activations.append(output)
        output.register_hook(lambda gradient: gradients.append(gradient))

    handle = model.features[-1].register_forward_hook(capture_activation)
    try:
        logits = model(x)
    finally:
        handle.remove()

    with torch.no_grad():
        flipped_logits = model(x.flip(dims=(3,)))
        temperature = float(getattr(model, "temperature", 1.0))
        view_predictions = torch.stack(
            (
                (logits / temperature).softmax(1)[0],
                (flipped_logits / temperature).softmax(1)[0],
            )
        )
        crop_probability = 1.0
        if allowed_classes is not None:
            crop_probability = float(
                view_predictions[:, allowed_classes].sum(dim=1).mean()
            )
            selected_predictions = view_predictions[:, allowed_classes]
            selected_probabilities = selected_predictions.mean(dim=0)
            probabilities = torch.zeros_like(view_predictions[0])
            probabilities[allowed_classes] = selected_probabilities
            stable = bool(
                selected_predictions[0].argmax()
                == selected_predictions[1].argmax()
            )
            top = allowed_classes[int(selected_probabilities.argmax())]
        else:
            probabilities = view_predictions.mean(dim=0)
            stable = bool(
                view_predictions[0].argmax() == view_predictions[1].argmax()
            )
            top = int(probabilities.argmax())

    model.zero_grad()
    logits[0, top].backward()
    activation, gradient = activations[0].detach(), gradients[0].detach()
    weights = gradient.mean(dim=(2, 3), keepdim=True)
    cam = torch.relu((weights * activation).sum(dim=1, keepdim=True))
    cam = F.interpolate(
        cam, size=x.shape[2:], mode="bilinear", align_corners=False
    )[0, 0]
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
    return probabilities.cpu().numpy(), cam.cpu().numpy(), stable, crop_probability
