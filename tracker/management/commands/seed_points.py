import json
import os
from django.core.management.base import BaseCommand
from tracker.models import PointTemplate

class Command(BaseCommand):
    help = 'Seeds PointTemplate rows from point_templates.json'

    import json
import os

from django.core.management.base import BaseCommand
from tracker.models import PointTemplate


class Command(BaseCommand):
    help = 'Seeds PointTemplate rows from point_templates.json'

    def handle(self, *args, **options):

        file_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            'point_templates.json'
        )

        with open(file_path, 'r', encoding='utf-8') as file:
            points = json.load(file)

        for point in points:

            PointTemplate.objects.update_or_create(
                point_no=point['point_no'],
                defaults={
                    'group': point['group'],
                    'title_kn': point['title_kn'],
                    'title_en': point['title_en'],
                    'columns': point['columns'],
                }
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded {len(points)} PointTemplate records.'
            )
        )