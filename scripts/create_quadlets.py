from pathlib import Path
from pprint import pprint
from os import makedirs
from shutil import copy
from jinja2 import Template


def main():
    scripts_dir = get_scripts_dir()
    quadlet_dir = create_quadlet_dir(scripts_dir=scripts_dir)
    create_content_volume(scripts_dir=scripts_dir, quadlet_dir=quadlet_dir)
    create_nginx_container(scripts_dir=scripts_dir, quadlet_dir=quadlet_dir)
    copy_static_quadlets(scripts_dir=scripts_dir, quadlet_dir=quadlet_dir)


def create_quadlet_dir(*, scripts_dir: Path) -> Path:
    quadlet_dir = scripts_dir.parent.joinpath("dist/quadlet")
    makedirs(quadlet_dir, exist_ok=True)
    return quadlet_dir


def get_scripts_dir() -> Path:
    return Path(__file__).parent.resolve(strict=True)


def create_content_volume(*, scripts_dir: Path, quadlet_dir: Path):
    content_dir = scripts_dir.parent.joinpath("data/content")
    template_path = scripts_dir.joinpath("templates/kaleido-api-content.volume.jinja2")

    with open(template_path) as f:
        template = Template(f.read())

    text = template.render(content_dir=str(content_dir))
    with open(quadlet_dir.joinpath("kaleido-api-content.volume"), "w") as f:
        f.write(text)


def create_nginx_container(*, scripts_dir: Path, quadlet_dir: Path):
    conf_d_dir = scripts_dir.parent.joinpath("data/nginx/conf.d")
    template_path = scripts_dir.joinpath("templates/kaleido-api-nginx.container.jinja2")

    with open(template_path) as f:
        template = Template(f.read())

    text = template.render(volume_dir=str(conf_d_dir))
    with open(quadlet_dir.joinpath("kaleido-api-nginx.container"), "w") as f:
        f.write(text)


def copy_static_quadlets(*, scripts_dir: Path, quadlet_dir: Path):
    repository_root_dir = scripts_dir.parent

    copy(
        src=repository_root_dir.joinpath("quadlets/kaleido-api.network"),
        dst=quadlet_dir.joinpath("kaleido-api.network"),
    )
    copy(
        src=repository_root_dir.joinpath("quadlets/kaleido-api-cloudflared.container"),
        dst=quadlet_dir.joinpath("kaleido-api-cloudflared.container"),
    )


if __name__ == "__main__":
    main()
