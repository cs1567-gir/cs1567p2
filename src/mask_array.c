#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define BLUE 0
#define RED  1
#define GREEN 2
#define BROWN 3

#define IMAGE_WIDTH  640
#define IMAGE_HEIGHT  480

#define NEW_BLOB_THRESHOLD 3
#define MAX_BLOBS 1024
#define MIN_BLOB_SIZE  200
#define MAX_BLOB_SIZE  3000


struct bgr {
    char b;
    char g;
    char r;
};

struct point2d {
    int x;
    int y;
};

struct point3d{
    int x;
    int y;
    int z;
};

struct blob {
    int xmin;
    int xmax;
    int ymin;
    int ymax;
    struct point2d center;
    int color;
    int size;
    struct point2d points[10000];
};

void add_to_blob(struct blob * blobs, int pixel, int color, int * numblobs){
    int i;
    int x;
    int y;
    int added;
    i = 0;
    added = 0;
    x = pixel % IMAGE_WIDTH;
    y = pixel / IMAGE_WIDTH;
    while(i < *numblobs && !added)
    {
        if(blobs[i].color == color &&
           (blobs[i].xmin - x < NEW_BLOB_THRESHOLD && x - blobs[i].xmax < NEW_BLOB_THRESHOLD) &&
           (blobs[i].ymin - y < NEW_BLOB_THRESHOLD && y - blobs[i].ymax < NEW_BLOB_THRESHOLD))
           {
               /* add to existing blob */
               blobs[i].points[blobs[i].size].x = x;
               blobs[i].points[blobs[i].size].y = y;
               /* set added to true */
               added = 1;
               if(x < blobs[i].xmin)
                   blobs[i].xmin = x;
               if(x > blobs[i].xmax)
                   blobs[i].xmax = x;
               if(y < blobs[i].ymin)
                   blobs[i].ymin = y;
               if(y > blobs[i].ymax)
                   blobs[i].ymax = y;
               blobs[i].size++;
           }
           i++;
    }
    if(!added){
        if(*numblobs == MAX_BLOBS){
            printf("TOO MANY BLOBS!\n");
        } else {
            blobs[*numblobs].color = color;
            blobs[*numblobs].xmin = x;
            blobs[*numblobs].xmax = x;
            blobs[*numblobs].ymin = y;
            blobs[*numblobs].ymax = y;
            blobs[*numblobs].points[0].x = x;
            blobs[*numblobs].points[0].y = y;
            blobs[*numblobs].size = 1;
            *numblobs += 1;
        }
    }
}

void find_centers(struct blob * blobs, int * numblobs, uint8_t * data)
{
    int i, j;
    int draw_x, draw_y;
    int sum_x;
    int sum_y;
    for(i = 0; i < *numblobs; i++)
    {
        sum_x = 0;
        sum_y = 0;
        if(blobs[i].size > MIN_BLOB_SIZE && blobs[i].size < MAX_BLOB_SIZE)
        {
            for(j = 0; j < blobs[i].size; j++)
            {
                sum_x += blobs[i].points[j].x;
                sum_y += blobs[i].points[j].y;
            }
            blobs[i].center.x = sum_x / blobs[i].size;
            blobs[i].center.y = sum_y / blobs[i].size;
/*
            printf("blob found... color: %i, center: (%i, %i), size: %i\n", blobs[i].color, blobs[i].center.x, blobs[i].center.y, blobs[i].size);
*/
            for(draw_x = blobs[i].center.x - 10; draw_x < blobs[i].center.x + 10; draw_x++) {
                for(draw_y = blobs[i].center.y - 10; draw_y < blobs[i].center.y + 10; draw_y++){
                    if(draw_x >= 0 && draw_y >= 0 && draw_x < 640 && draw_y < 480){
                        data[draw_x * 3 + draw_y * 640 *3] = 50;
                        data[draw_x * 3 + draw_y * 640 * 3 + 1] = 50;
                        data[draw_x * 3 + draw_y * 640 * 3 + 2] = 255;
                    }
                }
            }
        }

    }
}

void color_mask(uint8_t * data, int n, uint8_t * color_mask_list, int num_colors, int thresh){
    int pixel, color;
    uint8_t * result;
    result = malloc(3*n);
    memset(result, 0, 3*n);
    struct blob * all_blobs;
    all_blobs = malloc(MAX_BLOBS * sizeof(struct blob));
    int * numblobs = malloc(4);
    *numblobs = 0;

    for(pixel = 0; pixel < n; pixel++)
    {
        for(color = 0; color < num_colors; color++)
        {
            if((abs(data[3*pixel] - color_mask_list[3*color]) <= thresh) &&
               (abs(data[3*pixel+1] - color_mask_list[3*color+1]) <= thresh) &&
               (abs(data[3*pixel+2] - color_mask_list[3*color+2]) <= thresh))
            {
                result[3*pixel] = color_mask_list[3*color];
                result[3*pixel+1] = color_mask_list[3*color+1];
                result[3*pixel+2] = color_mask_list[3*color+2];
                add_to_blob(all_blobs, pixel, color, numblobs);
            }
        }
    }
    memcpy(data, result, n*3);
    find_centers(all_blobs, numblobs, data);
    free(all_blobs);
}
